from langchain_core.tools import tool
from app.marine_weather_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz
from app.chlorophyll_tool import get_chlorophyll_data
from app.boundary_toool import check_maritime_boundary
from app.historical import sagar_mitra_historical_query
from app.weather_alert_tool import get_weather_hazard_alerts
from app.statistical_engine import ArgoStatisticalAnomalyEngine
from app.regional_scan import scan_favorable_regions, format_regional_scan
from app.data import store as data_store
from app.state import AgentState
from app.dispatch import generate_morning_dispatch

# 1. Navigation & Hazard Worker (Powered by marine_weather_tool.py)
@tool
def check_marine_hazards(lat: float, lon: float) -> str:
    """Checks wave heights, temperature, and maritime hazards for given coordinates using live NOAA/Open-Meteo data."""
    return get_live_ocean_conditions(lat, lon)

def navigation_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    # graph.py's dispatch_node fetches this exact signal for EVERY request
    # (the dashboard needs it regardless of which agents were selected) and
    # threads it through state.common_signals -- reuse it instead of making
    # a second live call for the same coordinate. Falls back to a direct
    # fetch when called outside that flow (e.g. a standalone/test call with
    # no common_signals present).
    common = state.get("common_signals") or {}
    result = common.get("ocean_report") or get_live_ocean_conditions(
        lat, lon, day_offset=state.get("day_offset", 0), target_hour=state.get("target_hour"))
    return {
        "hazard_alerts": [result],
        "final_output": f"Navigation Report: {result}"
    }


# 2. Ocean & Fishing Worker (Powered by pfz_tool.py & chlorophyll_tool.py)
@tool
def check_pfz_and_chlorophyll(lat: float, lon: float) -> str:
    """Checks Potential Fishing Zones (PFZ) and chlorophyll concentration for fish aggregation."""
    pfz_result = get_nearest_pfz(lat, lon)
    chlorophyll_result = get_chlorophyll_data(lat, lon)
    return f"{pfz_result} | {chlorophyll_result}"

def fishing_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    # Reuse the PFZ/chlorophyll reads graph.py's dispatch_node already
    # fetched for the dashboard (see navigation_node's comment above) rather
    # than calling the same two APIs again here.
    common = state.get("common_signals") or {}
    pfz_result = common.get("pfz_report") or get_nearest_pfz(lat, lon)
    chlorophyll_result = common.get("chlorophyll_report") or get_chlorophyll_data(lat, lon)
    result = f"{pfz_result} | {chlorophyll_result}"

    # PFZ/chlorophyll have no forecast product -- they're always "today
    # only" (see main.py). Wave/weather/hazard data CAN answer a future-
    # dated query ("is it safe tomorrow morning?"), so without this note a
    # synthesized advisory could silently read as if the PFZ/chlorophyll
    # figures were forecast for that same future time too. Label them
    # explicitly whenever the query carried a future date/time, so the
    # synthesizer (app/advisory.py) has to preserve the distinction instead
    # of quietly blending the two.
    is_future_query = state.get("day_offset", 0) > 0 or state.get("target_hour") is not None
    if is_future_query:
        result += (
            " [Note: the PFZ and chlorophyll readings above are TODAY's CURRENT/LIVE data, "
            "not a forecast for the requested future date/time -- no forecast product exists "
            "yet for these two signals. Only wave/weather/hazard data elsewhere in this "
            "advisory reflects the requested future time.]"
        )

    return {
        "final_output": f"Fishing Advisory: {result}"
    }


# 3. Compliance & Boundary Worker (Powered by boundary_toool.py)
@tool
def check_legal_boundaries(lat: float, lon: float) -> str:
    """Checks if coordinates violate Marine Protected Areas (MPA) or cross the Indian EEZ boundary."""
    return check_maritime_boundary(lat, lon)

def compliance_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    common = state.get("common_signals") or {}
    result = common.get("boundary_report") or check_legal_boundaries.invoke({"lat": lat, "lon": lon})
    return {
        "final_output": f"Compliance Report: {result}"
    }


# 4. Historical & Trend Worker (Powered by historical.py's Gemini
# function-calling agent -- was fully built but had no live route pointing
# at it; wired in here so "why did X decline" / trend / chart questions
# actually reach it instead of falling through to a generic answer.)
def historical_node(state: AgentState) -> dict:
    result = sagar_mitra_historical_query(
        state.get("user_message", ""),
        persona=state.get("persona", "Fisherman"),
        language=state.get("language", "English"),
    )
    text = result.get("reply") or "No historical data available for that query."
    out = {"final_output": f"Historical Analysis: {text}"}
    if result.get("plot_url"):
        out["final_output"] += f"\n[Chart generated: {result['plot_url']}]"
        out["plot_url"] = result["plot_url"]
    if result.get("series"):
        out["historical_series"] = result["series"]
    return out


# 5. Hazard Worker (lightning / cyclone proxy, powered by weather_alert_tool.py)
def hazard_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    common = state.get("common_signals") or {}
    result = common.get("hazard_report") or get_weather_hazard_alerts(
        lat, lon, day_offset=state.get("day_offset", 0), target_hour=state.get("target_hour"))
    alerts = [result["summary"]] if (result["lightning_alert"] or result["cyclone_alert"]) else []
    return {
        "final_output": f"Hazard Alert: {result['lightning_detail']} {result['cyclone_detail']}",
        "hazard_alerts": alerts,
    }


# 6. Ocean Analytics Worker (Powered by statistical_engine.py's 4-tier
# anomaly engine + real Argo data -- was fully built but had no live route;
# wired in here for "why is this unusual" / anomaly-style questions.)
def analytics_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    profile_df = data_store.get_real_profile_near(lat, lon)
    if profile_df is None:
        return {"final_output": "Ocean Analytics: Not enough real nearby ocean-profile "
                                 "data to run statistical anomaly detection at this location."}

    hist_df = data_store.get_real_hist_near(lat, lon)
    engine = ArgoStatisticalAnomalyEngine(climatology_db=data_store.calibrated_clim)
    result = engine.analyze_profile(profile_df, historical_timeseries=hist_df)

    anomalies = result.get("detected_anomalies", [])
    if anomalies:
        summary = " / ".join(
            f"{a['anomaly_type']} (severity {a['severity']}): {a['oceanographic_summary']}"
            for a in anomalies
        )
    else:
        summary = "No statistically significant anomalies detected against the calibrated baseline."

    lm = result.get("layer_metrics", {})
    evidence = f"Mixed Layer Depth {lm.get('MLD')}m, Isothermal Layer Depth {lm.get('ILD')}m, Barrier Layer {lm.get('BLT')}m"
    return {"final_output": f"Ocean Analytics: {summary} ({evidence})"}


# 7. Regional Worker (Powered by regional_scan.py -- ranks today's real PFZ
# zones by chlorophyll/SST/ML-confidence, for "which regions look
# favorable" style questions the single-point tools above can't answer.)
def regional_node(state: AgentState) -> dict:
    results = scan_favorable_regions(top_n=5)
    # `regional_zones` is surfaced as its own top-level API field (see
    # graph.py's dispatch_node and main.py) so the frontend can plot the
    # ranked zones as map markers directly, instead of only ever getting
    # them as prose inside the advisory text.
    return {"final_output": format_regional_scan(results), "regional_zones": results}


# 8. Morning Dispatch Worker (Powered by dispatch.py -- generates the
# downloadable PDF + audio briefing itself, rather than just describing
# live conditions like every other agent above). Named morning_dispatch_
# node, not dispatch_node, so it can't collide with graph.py's own
# dispatch_node (the orchestration step that fans out to every agent below
# -- an unrelated function that happens to share the "dispatch" word).
def morning_dispatch_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    persona = state.get("persona", "Fisherman")
    language = state.get("language", "English")
    vessel_persona = state.get("vessel_persona", "artisanal_coastal")
    day_offset = state.get("day_offset", 0)
    target_hour = state.get("target_hour")
    # Deliberately does NOT reuse state["common_signals"] here -- this
    # agent runs CONCURRENTLY with that fetch (see graph.py, where
    # "dispatch" is NOT in _COMMON_SIGNAL_AGENTS), so generate_morning_
    # dispatch's own full six-way concurrent fetch starts immediately
    # instead of waiting for the common fetch to resolve first. See
    # dispatch.py's generate_morning_dispatch docstring for why that
    # reuse was tried and reverted -- it made this path slower overall.
    result = generate_morning_dispatch(
        lat, lon, persona=persona, language=language, vessel_persona=vessel_persona,
        day_offset=day_offset, target_hour=target_hour if target_hour is not None else 8,
    )

    audio_note = (f" Spoken version: {result['audio_url']}." if result["audio_url"]
                  else " (Spoken audio version unavailable this time -- PDF only.)")
    # Lead with dispatch.py's OWN already-grounded narrative (it ran its own
    # synthesize_advisory pass over the REAL fetched signals -- see
    # generate_morning_dispatch) rather than just a bare "download your PDF"
    # pointer sentence. An earlier version only sent the pointer sentence up
    # through final_output, which left graph.py's top-level synthesizer with
    # nothing real to ground a persona-formatted chat reply in -- verified
    # live, it produced a DIFFERENT, non-deterministic safety verdict on
    # each run ("Safe to Sail" one time, "No-Go Warning" the next, from
    # identical input) because there was no real data for it to read, only
    # a link. Including the real narrative here, plus graph.py's dispatch-
    # only bypass below, keeps the chat reply consistent with what the
    # PDF/audio actually say.
    text = f"{result['narrative']}\n\nFull offline briefing: {result['pdf_url']}.{audio_note}"
    return {
        "final_output": f"Morning Dispatch: {text}",
        # Exposed as their OWN top-level API fields (see graph.py's
        # dispatch_node and main.py), matching the plot_url/regional_zones
        # pattern above -- a Gemini synthesis pass could otherwise
        # paraphrase away a raw download URL embedded only in prose.
        "dispatch_pdf_url": result["pdf_url"],
        "dispatch_audio_url": result["audio_url"],
    }