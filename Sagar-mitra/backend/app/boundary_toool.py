import json
import math
import os
from typing import List, Optional

from shapely.geometry import Point, shape
from shapely.ops import nearest_points

base_path = os.path.dirname(__file__)
eez_path = os.path.join(base_path, '..', 'data', 'india_eez.geojson')
mpa_path = os.path.join(base_path, '..', 'data', 'india_mpas.geojson')

def load_geometries(filepath):
    """Parses GeoJSON using standard json + shapely to avoid pyogrio/GDAL issues."""
    geometries = []
    if not os.path.exists(filepath):
        return geometries
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for feature in data.get('features', []):
            geom = feature.get('geometry')
            if geom:
                geometries.append(shape(geom))
    return geometries

# Load boundaries without GeoPandas
eez_geoms = load_geometries(eez_path)
mpa_geoms = load_geometries(mpa_path)

def check_maritime_boundary(lat: float, lon: float) -> str:
    """
    Deterministic geometry check -- returns a factual, literal statement of
    what was actually determined. Never asserts a "safe"/"legal" status
    unless the relevant boundary data was actually loaded and checked; if
    EEZ or MPA reference data is missing, that gap is stated explicitly so
    the compliance advisory layer downstream never reports a confident
    status it hasn't earned.
    """
    pt = Point(lon, lat)
    coord_label = f"[{lat}, {lon}]"

    missing = []
    if not eez_geoms:
        missing.append("EEZ boundary data")
    if not mpa_geoms:
        missing.append("MPA boundary data")

    if eez_geoms and not any(geom.contains(pt) for geom in eez_geoms):
        return f"ALERT: {coord_label} has crossed into international waters."

    if mpa_geoms and any(geom.contains(pt) for geom in mpa_geoms):
        return f"ALERT: {coord_label} is inside a Marine Protected Area (MPA)."

    if missing:
        return (f"UNVERIFIED: {coord_label} did not trigger any known EEZ or MPA "
                f"violation, but {' and '.join(missing)} is not loaded on this "
                f"server, so compliance status cannot be fully confirmed. Do not "
                f"report this as a confirmed 'safe' or 'legal' status.")

    return f"{coord_label} is confirmed within Indian waters and outside all known Marine Protected Areas."

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Same formula as route_planner.py's _haversine_km / pfz_tool.py's
    calculate_distance -- kept local here rather than imported so this
    module has no dependency on the routing code, but shapely's own raw
    .distance() (plain lon/lat degrees) is deliberately never used for a
    kilometer figure below: at these latitudes a degree of longitude is
    meaningfully shorter than a degree of latitude, which would quietly
    distort a 5km geofence threshold."""
    R = 6371.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _distance_to_boundary_line_km(pt: Point, geoms: List) -> Optional[float]:
    """Distance in km from `pt` to the nearest EDGE of any geometry in
    `geoms`, regardless of which side `pt` is on. Used for the EEZ: a
    vessel approaching the line from inside Indian waters is exactly the
    case the proactive geofence siren needs to catch, not just a confirmed
    breach after the fact (see check_maritime_boundary above)."""
    if not geoms:
        return None
    best = None
    for geom in geoms:
        nearest_on_edge, _ = nearest_points(geom.boundary, pt)
        dist = _haversine_km(pt.y, pt.x, nearest_on_edge.y, nearest_on_edge.x)
        best = dist if best is None else min(best, dist)
    return round(best, 3) if best is not None else None


def _distance_to_area_km(pt: Point, geoms: List) -> Optional[float]:
    """Distance in km from `pt` to the nearest AREA among `geoms` -- 0.0 if
    `pt` already sits inside one of them (shapely's nearest_points treats a
    Polygon as a filled area, so the nearest point to an interior `pt` is
    `pt` itself), otherwise the real distance to its nearest edge. Used for
    MPAs: being inside is already a full violation (see
    check_maritime_boundary), so the only useful proximity signal here is
    "how close before entering one", not how deep inside."""
    if not geoms:
        return None
    best = None
    for geom in geoms:
        nearest_on_geom, _ = nearest_points(geom, pt)
        dist = _haversine_km(pt.y, pt.x, nearest_on_geom.y, nearest_on_geom.x)
        best = dist if best is None else min(best, dist)
    return round(best, 3) if best is not None else None


def distance_to_nearest_boundary_km(lat: float, lon: float) -> dict:
    """
    Proactive geofence check (Feature 3 -- "5km threshold"): unlike
    check_maritime_boundary's binary inside/outside verdict, this reports
    actual live proximity in kilometers so a caller (see main.py's
    GET /api/geofence-check) can warn a vessel BEFORE it crosses out of the
    EEZ or into an MPA, not only after the fact.

    Returns:
        {
          "eez_distance_km": float | None,  # distance to the nearest EEZ
              boundary LINE, whichever side of it the vessel is on
              (None if EEZ data isn't loaded)
          "inside_eez": bool | None,        # None if EEZ data isn't loaded
          "mpa_distance_km": float | None,  # distance to the nearest MPA
              AREA; 0.0 if already inside one (None if MPA data isn't loaded)
          "inside_mpa": bool,
          "missing_data": [str, ...],       # which reference layers, if any, aren't loaded
        }
    """
    pt = Point(lon, lat)

    missing = []
    if not eez_geoms:
        missing.append("EEZ boundary data")
    if not mpa_geoms:
        missing.append("MPA boundary data")

    inside_eez = any(geom.contains(pt) for geom in eez_geoms) if eez_geoms else None
    inside_mpa = any(geom.contains(pt) for geom in mpa_geoms) if mpa_geoms else False

    return {
        "eez_distance_km": _distance_to_boundary_line_km(pt, eez_geoms),
        "inside_eez": inside_eez,
        "mpa_distance_km": _distance_to_area_km(pt, mpa_geoms),
        "inside_mpa": inside_mpa,
        "missing_data": missing,
    }


DEG_TO_KM = 111.0  # approx km per decimal degree, used only for the quick geofence check below


def distance_to_boundary_km(lat: float, lon: float) -> Optional[float]:
    """
    Quick geofence distance check (Task 3 / GET /api/geofence-check):
    plain shapely `.distance()` (decimal degrees) against the loaded EEZ
    MultiPolygons, scaled by DEG_TO_KM. Approximate by design -- unlike
    distance_to_nearest_boundary_km's haversine-based figure above, this
    doesn't correct for longitude convergence at latitude, so it's meant
    for a coarse "close to the line" caution flag, not a precise reading.
    Returns None if no EEZ boundary data is loaded.
    """
    if not eez_geoms:
        return None
    pt = Point(lon, lat)
    best = min(geom.boundary.distance(pt) for geom in eez_geoms)
    return round(best * DEG_TO_KM, 3)


if __name__ == "__main__":
    # Test coordinate off Mumbai coast
    print(check_maritime_boundary(18.9, 72.8))
    print(distance_to_nearest_boundary_km(18.9, 72.8))