from langchain_core.tools import tool
from app.satellite_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz
from app.chlorophyll_tool import get_chlorophyll_data
from app.boundary_toool import check_maritime_boundary
from app.historical import sagar_mitra_historical_query
from app.weather_alert_tool import get_weather_hazard_alerts
from app.statistical_engine import ArgoStatisticalAnomalyEngine
from app.data import store as data_store
from app.state import AgentState

# 1. Navigation & Hazard Worker (Powered by satellite_tool.py)
@tool
def check_marine_hazards(lat: float, lon: float) -> str:
    """Checks wave heights, temperature, and maritime hazards for given coordinates using live NOAA/Open-Meteo data."""
    return get_live_ocean_conditions(lat, lon)

def navigation_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    result = check_marine_hazards.invoke({"lat": lat, "lon": lon})
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
    result = check_pfz_and_chlorophyll.invoke({"lat": lat, "lon": lon})
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
    result = check_legal_boundaries.invoke({"lat": lat, "lon": lon})
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
    return out


# 5. Hazard Worker (lightning / cyclone proxy, powered by weather_alert_tool.py)
def hazard_node(state: AgentState) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    result = get_weather_hazard_alerts(lat, lon)
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