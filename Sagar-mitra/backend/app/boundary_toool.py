import json
import os
from shapely.geometry import Point, shape

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

if __name__ == "__main__":
    # Test coordinate off Mumbai coast
    print(check_maritime_boundary(18.9, 72.8))