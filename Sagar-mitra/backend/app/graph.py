from concurrent.futures import ThreadPoolExecutor

from langgraph.graph import StateGraph, END

# Import the real worker nodes -- one function per specialized agent domain
from app.sub_agents import (
    navigation_node, fishing_node, compliance_node,
    historical_node, hazard_node, analytics_node, regional_node,
    morning_dispatch_node,
)

# Gemini formatters that keep persona/language/grounding rules
from app.advisory import synthesize_advisory, format_compliance_advisory, require_gemini_key

# LLM planner: decomposes the query into the set of agents to run, plus
# detected language/persona/intent (replaces the old single-keyword router)
from app.planner import plan_query

# Deterministic, localized fallback formatting + error sanitization -- used
# whenever Gemini itself is unavailable, so a quota/outage degrades the
# FORMATTING and LANGUAGE gracefully instead of leaking a raw API error or
# falling back to unlabeled, English-only, wall-of-text concatenation.
from app.response_formatter import format_natural_fallback_advisory, derive_hazard_status
from app.error_utils import safe_error_text

# The five "common" live-data lookups that BOTH the corresponding chat
# agents (navigation/fishing/compliance/hazard) AND main.py's dashboard
# telemetry/hazard-banner/PFZ-map/route derivation need on every request,
# regardless of which agents the planner actually picked. Fetching them
# once here (concurrently) and threading the result through `state` is
# what lets main.py stop re-fetching this exact data a second time after
# the graph already ran it -- previously ~2x the external API calls per
# query.
from app.boundary_toool import check_maritime_boundary
from app.marine_weather_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz
from app.chlorophyll_tool import get_chlorophyll_data
from app.weather_alert_tool import get_weather_hazard_alerts

# The shared state dictionary (the backpack that passes data between nodes)
from app.state import AgentState

AGENT_FUNCS = {
    "navigation": navigation_node,
    "fishing": fishing_node,
    "compliance": compliance_node,
    "historical": historical_node,
    "hazard": hazard_node,
    "analytics": analytics_node,
    "regional": regional_node,
    "dispatch": morning_dispatch_node,
}

# Agents whose report is built entirely from one of the five common signals
# fetched below -- these must wait for that fetch, but don't need to make
# any live call of their own once it lands (see sub_agents.py). "dispatch"
# is deliberately NOT here: morning_dispatch_node runs its own full,
# independent six-way concurrent fetch (see dispatch.py), so it belongs in
# the independent_futures pool below and should start immediately,
# concurrently with the common fetch, not wait on it -- an earlier version
# put it here to reuse common_signals, but that serialized the slow
# regional-zone scan after the common fetch instead of overlapping it,
# making the chat-triggered dispatch path slower overall (see dispatch.py's
# generate_morning_dispatch docstring).
_COMMON_SIGNAL_AGENTS = {"navigation", "fishing", "compliance", "hazard"}

_HAZARD_REPORT_FALLBACK = {
    "lightning_alert": False, "lightning_detail": "Hazard data unavailable.",
    "cyclone_alert": False, "cyclone_detail": "Hazard data unavailable.",
    "summary": "Hazard data unavailable.",
}


def _fetch_common_signals(pool: ThreadPoolExecutor, lat: float, lon: float,
                           day_offset: int, target_hour) -> dict:
    """Fires all five common live-data lookups at once (I/O-bound, so a
    thread pool -- same pattern as regional_scan.py's zone scan) instead of
    fetching them one at a time, which is what made a single query take
    20+ seconds end to end."""
    return {
        "boundary_report": pool.submit(check_maritime_boundary, lat, lon),
        "ocean_report": pool.submit(get_live_ocean_conditions, lat, lon,
                                     day_offset=day_offset, target_hour=target_hour),
        "pfz_report": pool.submit(get_nearest_pfz, lat, lon),
        "chlorophyll_report": pool.submit(get_chlorophyll_data, lat, lon),
        "hazard_report": pool.submit(get_weather_hazard_alerts, lat, lon,
                                      day_offset=day_offset, target_hour=target_hour),
    }


def _resolve_common_signals(futures: dict) -> dict:
    """Resolves each future independently so one flaky fetch can't mask the
    other four (mirrors the 'never let a raw exception reach agent_reports'
    guard already used for agent execution below)."""
    signals = {}
    for key, future in futures.items():
        try:
            signals[key] = future.result()
        except Exception as e:
            print(f"[dispatch] common signal '{key}' fetch failed: {e}")
            signals[key] = dict(_HAZARD_REPORT_FALLBACK) if key == "hazard_report" else f"Data unavailable: {e}"
    return signals


def _call_agent(fn, agent_name: str, state: AgentState, language: str) -> dict:
    try:
        return fn(state)
    except Exception as e:
        # Never let a raw exception (e.g. a Gemini 429/503 JSON body from
        # historical_node's Gemini call) reach agent_reports -- it flows
        # straight into the advisory text from here.
        print(f"[dispatch] {agent_name} agent failed: {e}")
        return {"final_output": safe_error_text(e, language)}


def create_orca_graph():
    # Strict startup check: fails fast with clear terminal instructions if
    # no Gemini key is configured, instead of silently compiling a graph
    # where every request will quietly degrade to the raw-data fallback
    # formatter with no visible signal that a key was never set.
    require_gemini_key()

    workflow = StateGraph(AgentState)

    # 1. Planner Node -- LLM-based multi-agent decomposition (with a
    # deterministic keyword fallback baked into plan_query itself, so a
    # Gemini outage degrades routing quality but never breaks the request).
    # Sees recent conversation history so referential follow-ups ("those
    # same conditions", "what about tomorrow instead") can be resolved
    # against what was just discussed, and falls back to the PREVIOUS
    # turn's agent selection (last_agents) rather than an unrelated
    # keyword-default guess when the new message matches no keyword.
    def planner_node(state: AgentState):
        print("--- PLANNER: Decomposing user request ---")
        plan = plan_query(
            state.get("user_message", ""),
            history=state.get("history", []),
            last_agents=state.get("last_agents", []),
        )
        state["next_steps"] = plan["agents"]
        state["language"] = plan["language"]
        state["persona"] = plan["persona"]
        state["query_intent"] = plan["query_intent"]
        print(f"--- PLANNER: agents={plan['agents']} language={plan['language']} persona={plan['persona']} ---")
        return state

    # 2. Dispatch Node -- runs every agent the planner selected CONCURRENTLY
    # (thread pool, since these are independent I/O-bound calls -- the same
    # pattern regional_scan.py already uses for its multi-zone fetch), and
    # ALSO fetches the five "common" signals (boundary/ocean/PFZ/
    # chlorophyll/hazard) unconditionally in the same pool, since main.py
    # needs them for the dashboard on every request regardless of which
    # agents were selected. Storing them in `state["common_signals"]` lets
    # main.py reuse this result instead of re-fetching it after the graph
    # returns.
    def dispatch_node(state: AgentState):
        agents_to_run = state.get("next_steps", []) or ["compliance"]
        print(f"--- DISPATCH: Running {agents_to_run} (parallel) ---")
        language = state.get("language", "English")
        coordinates = state.get("coordinates", [18.9, 72.8])
        lat, lon = coordinates[0], coordinates[1]
        day_offset = state.get("day_offset", 0)
        target_hour = state.get("target_hour")

        with ThreadPoolExecutor(max_workers=len(agents_to_run) + 5) as pool:
            # Fire the common fetch immediately...
            common_futures = _fetch_common_signals(pool, lat, lon, day_offset, target_hour)

            # ...and, in the SAME pool at the SAME time, every requested
            # agent whose data source does NOT overlap with it (historical/
            # analytics/regional) -- no reason to wait for the common fetch
            # to land before starting these.
            independent_futures = {
                name: pool.submit(_call_agent, AGENT_FUNCS[name], name, state, language)
                for name in agents_to_run
                if name in AGENT_FUNCS and name not in _COMMON_SIGNAL_AGENTS
            }

            # Resolve the common signals and thread them into state so the
            # navigation/fishing/compliance/hazard agents below build their
            # report straight from data already in hand -- no extra call.
            common_signals = _resolve_common_signals(common_futures)
            state["common_signals"] = common_signals

            overlap_futures = {
                name: pool.submit(_call_agent, AGENT_FUNCS[name], name, state, language)
                for name in agents_to_run
                if name in _COMMON_SIGNAL_AGENTS and name in AGENT_FUNCS
            }

            all_futures = {**independent_futures, **overlap_futures}
            results = {name: future.result() for name, future in all_futures.items()}

        reports: dict = {}
        hazard_alerts = list(state.get("hazard_alerts", []))
        plot_url = None
        historical_series = None
        regional_zones: list = []
        dispatch_pdf_url = None
        dispatch_audio_url = None

        # Merge in agents_to_run order (not completion order) so the
        # combined report text stays deterministic regardless of which
        # agent's I/O happened to finish first.
        for agent_name in agents_to_run:
            out = results.get(agent_name)
            if out is None:
                continue
            reports[agent_name] = out.get("final_output", "")
            hazard_alerts.extend(out.get("hazard_alerts", []))
            plot_url = out.get("plot_url", plot_url)
            historical_series = out.get("historical_series", historical_series)
            regional_zones = out.get("regional_zones", regional_zones)
            dispatch_pdf_url = out.get("dispatch_pdf_url", dispatch_pdf_url)
            dispatch_audio_url = out.get("dispatch_audio_url", dispatch_audio_url)

        state["agent_reports"] = reports
        state["hazard_alerts"] = hazard_alerts
        state["common_signals"] = common_signals
        # Exposed as their OWN top-level API fields (see main.py) instead of
        # only living inside the free-text advisory, where a Gemini
        # synthesis pass can freely paraphrase (or drop) a raw URL/JSON
        # blob embedded in prose.
        state["plot_url"] = plot_url
        state["historical_series"] = historical_series
        state["regional_zones"] = regional_zones
        state["dispatch_pdf_url"] = dispatch_pdf_url
        state["dispatch_audio_url"] = dispatch_audio_url
        # final_output is kept only as a plain-text join for the Gemini
        # synthesis prompt below; the FALLBACK path uses the structured
        # `agent_reports` dict directly instead, so it never has to
        # re-parse this string.
        state["final_output"] = "\n\n".join(reports.values())
        if plot_url:
            state["final_output"] += f"\n\n[plot_url]: {plot_url}"
        return state

    # 3. Synthesizer Node (combines all agent reports and formats via Gemini)
    def synthesizer_node(state: AgentState):
        raw_output = state.get("final_output", "Standard maritime check complete.")
        agent_reports = state.get("agent_reports", {})
        persona = state.get("persona", "Fisherman")
        language = state.get("language", "English")
        vessel_persona = state.get("vessel_persona", "artisanal_coastal")
        agents_run = state.get("next_steps", [])

        if agents_run == ["historical"]:
            # Chart/dataset-only queries (see planner.py's
            # _INSTANT_HISTORICAL_KEYWORDS fast path) need no Gemini prose at
            # all -- the real answer is the chart itself
            # (telemetry.historical_series, rendered by script.js), not a
            # narrated summary of numbers already visible in it. Skipping
            # Gemini here removes the last LLM call on this query path
            # entirely: no network calls, immune to a 503/timeout. Scoped to
            # EXACTLY ["historical"] (not "historical is present") so a
            # compound query that also picked navigation/fishing/etc. still
            # gets those agents' findings synthesized properly instead of
            # silently discarded.
            #
            # Text picked from the REAL chart_type the historical agent
            # actually produced this turn (historical.py's
            # plot_yearly_trend -> "line" vs plot_category_distribution /
            # plot_hazard_category_distribution -> "pie"), not guessed from
            # keywords, so it never describes a chart that isn't there.
            series = state.get("historical_series") or {}
            if series.get("chart_type") == "line":
                state["final_advisory"] = (
                    "Historical sea surface temperature data loaded. Displaying multi-year "
                    "oceanographic trendline below."
                )
            else:
                state["final_advisory"] = (
                    "Historical oceanographic telemetry and hazard distribution retrieved "
                    "successfully. Displaying interactive dataset breakdown below."
                )
            state["advisory_degraded"] = False
            return state

        print("--- SYNTHESIZER: Formatting combined advisory via Gemini ---")
        try:
            if agents_run == ["compliance"]:
                # A pure legal/boundary question: keep the strict,
                # non-inventive compliance formatter instead of the general
                # synthesis path, so legal findings are reported exactly as
                # computed and never embellished.
                polished_advisory = format_compliance_advisory(
                    raw_report=raw_output, persona=persona, language=language,
                    vessel_persona=vessel_persona,
                )
            elif agents_run == ["dispatch"]:
                # morning_dispatch_node's final_output already IS a fully
                # synthesized, persona/language-aware narrative -- dispatch.py
                # ran its own synthesize_advisory pass over the real fetched
                # signals (see generate_morning_dispatch), not a placeholder.
                # Re-synthesizing it again here would ask Gemini to rewrite
                # an already-good answer from scratch with nothing new to add,
                # at the cost of a second full Gemini call (measured: tens of
                # seconds) -- and, worse, if this bypass didn't exist and
                # final_output were ever just a short pointer sentence again,
                # a second pass with no real grounding could invent a safety
                # verdict not backed by data (see morning_dispatch_node's
                # comment for what that looked like in testing).
                polished_advisory = raw_output
            else:
                history = state.get("history", [])
                history_text = "\n".join(f"{t['role']}: {t['text']}" for t in history[-4:])
                polished_advisory = synthesize_advisory(
                    raw_report=raw_output,
                    persona=persona,
                    language=language,
                    vessel_persona=vessel_persona,
                    user_message=state.get("user_message", ""),
                    history_text=history_text,
                )
            state["final_advisory"] = polished_advisory
            state["advisory_degraded"] = False
        except Exception as e:
            # Gemini unavailable (quota/outage/503-high-demand/timeout --
            # see advisory.LLM_CALL_TIMEOUT_S): degrade gracefully to a
            # clean, per-agent, language-labeled response built directly
            # from the structured agent_reports dict -- never the raw
            # exception text, and never an unlabeled wall of concatenated
            # English strings. Flagged so main.py can surface this as
            # status: "ADVISORY_BUSY" instead of silently claiming success.
            #
            # The advisory TEXT itself deliberately does not expose "AI
            # busy"/infrastructure wording -- format_natural_fallback_advisory
            # builds a calm, natural paragraph from the real gathered
            # telemetry instead (see that function's docstring). Its
            # Operational Status line is computed from the REAL hazard_status
            # (derive_hazard_status, shared with main.py) rather than assumed
            # safe -- this is a safety advisory, so a degraded response must
            # never claim conditions are fine when they aren't, even while
            # reading cleanly.
            print(f"[Synthesizer Error] Falling back to formatted raw output: {e}")
            common = state.get("common_signals") or {}
            hazard_status = derive_hazard_status(
                common.get("boundary_report", ""), common.get("ocean_report", ""),
                common.get("hazard_report") or {},
            )
            state["final_advisory"] = format_natural_fallback_advisory(
                agent_reports, hazard_status, language=language,
            )
            state["advisory_degraded"] = True

        return state

    # Register all nodes into the graph
    workflow.add_node("planner", planner_node)
    workflow.add_node("dispatch", dispatch_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Linear pipeline: plan -> run every selected agent -> synthesize.
    # Fan-out across agents (AND the common-signal fetch) happens INSIDE
    # dispatch_node via a thread pool (see above), so the graph topology
    # itself stays simple and doesn't need parallel-branch reducers.
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "dispatch")
    workflow.add_edge("dispatch", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()
