from langchain_core.tools import tool
from app.satellite_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz
from app.chlorophyll_tool import get_chlorophyll_data
from app.boundary_toool import check_maritime_boundary

# 1. Navigation & Hazard Worker (Powered by satellite_tool.py)
@tool
def check_marine_hazards(lat: float, lon: float) -> str:
    """Checks wave heights, temperature, and maritime hazards for given coordinates using live NOAA/Open-Meteo data."""
    return get_live_ocean_conditions(lat, lon)

def navigation_node(state: dict) -> dict:
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

def fishing_node(state: dict) -> dict:
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

def compliance_node(state: dict) -> dict:
    coordinates = state.get("coordinates", [18.9, 72.8])
    lat, lon = coordinates[0], coordinates[1]
    result = check_legal_boundaries.invoke({"lat": lat, "lon": lon})
    return {
        "final_output": f"Compliance Report: {result}"
    }