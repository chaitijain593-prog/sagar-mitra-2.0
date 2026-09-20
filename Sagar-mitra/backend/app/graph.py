from langgraph.graph import StateGraph, END

# Import the real worker nodes -- one function per specialized agent domain
from app.sub_agents import (
    navigation_node, fishing_node, compliance_node,
    historical_node, hazard_node, analytics_node,
)

# Gemini formatters that keep persona/language/grounding rules
from app.advisory import synthesize_advisory, format_compliance_advisory

# LLM planner: decomposes the query into the set of agents to run, plus
# detected language/persona/intent (replaces the old single-keyword router)
from app.planner import plan_query

# Deterministic, localized fallback formatting + error sanitization -- used
# whenever Gemini itself is unavailable, so a quota/outage degrades the
# FORMATTING and LANGUAGE gracefully instead of leaking a raw API error or
# falling back to unlabeled, English-only, wall-of-text concatenation.
from app.response_formatter import format_fallback_advisory
from app.error_utils import safe_error_text

# The shared state dictionary (the backpack that passes data between nodes)
from app.state import AgentState

AGENT_FUNCS = {
    "navigation": navigation_node,
    "fishing": fishing_node,
    "compliance": compliance_node,
    "historical": historical_node,
    "hazard": hazard_node,
    "analytics": analytics_node,
}


def create_orca_graph():
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

    # 2. Dispatch Node -- runs every agent the planner selected (multi-agent
    # fan-out) and merges their reports. Implemented as one node that loops
    # over the selected worker functions, rather than LangGraph parallel
    # branches, so merging their outputs doesn't need custom reducers.
    def dispatch_node(state: AgentState):
        agents_to_run = state.get("next_steps", []) or ["compliance"]
        print(f"--- DISPATCH: Running {agents_to_run} ---")
        reports: dict = {}
        hazard_alerts = list(state.get("hazard_alerts", []))
        plot_url = None
        language = state.get("language", "English")

        for agent_name in agents_to_run:
            fn = AGENT_FUNCS.get(agent_name)
            if not fn:
                continue
            try:
                out = fn(state)
            except Exception as e:
                # Never let a raw exception (e.g. a Gemini 429/503 JSON body
                # from historical_node's Gemini call) reach agent_reports --
                # it flows straight into the advisory text from here.
                print(f"[dispatch] {agent_name} agent failed: {e}")
                out = {"final_output": safe_error_text(e, language)}
            reports[agent_name] = out.get("final_output", "")
            hazard_alerts.extend(out.get("hazard_alerts", []))
            plot_url = out.get("plot_url", plot_url)

        state["agent_reports"] = reports
        state["hazard_alerts"] = hazard_alerts
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
        print("--- SYNTHESIZER: Formatting combined advisory via Gemini ---")
        raw_output = state.get("final_output", "Standard maritime check complete.")
        agent_reports = state.get("agent_reports", {})
        persona = state.get("persona", "Fisherman")
        language = state.get("language", "English")
        agents_run = state.get("next_steps", [])

        try:
            if agents_run == ["compliance"]:
                # A pure legal/boundary question: keep the strict,
                # non-inventive compliance formatter instead of the general
                # synthesis path, so legal findings are reported exactly as
                # computed and never embellished.
                polished_advisory = format_compliance_advisory(
                    raw_report=raw_output, persona=persona, language=language,
                )
            else:
                history = state.get("history", [])
                history_text = "\n".join(f"{t['role']}: {t['text']}" for t in history[-4:])
                polished_advisory = synthesize_advisory(
                    raw_report=raw_output,
                    persona=persona,
                    language=language,
                    user_message=state.get("user_message", ""),
                    history_text=history_text,
                )
            state["final_advisory"] = polished_advisory
        except Exception as e:
            # Gemini unavailable (quota/outage): degrade gracefully to a
            # clean, per-agent, language-labeled response built directly
            # from the structured agent_reports dict -- never the raw
            # exception text, and never an unlabeled wall of concatenated
            # English strings.
            print(f"[Synthesizer Error] Falling back to formatted raw output: {e}")
            state["final_advisory"] = format_fallback_advisory(agent_reports, language=language)

        return state

    # Register all nodes into the graph
    workflow.add_node("planner", planner_node)
    workflow.add_node("dispatch", dispatch_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Linear pipeline: plan -> run every selected agent -> synthesize.
    # Fan-out across agents happens INSIDE dispatch_node (see above), so the
    # graph topology itself stays simple and doesn't need parallel-branch
    # reducers.
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "dispatch")
    workflow.add_edge("dispatch", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()
