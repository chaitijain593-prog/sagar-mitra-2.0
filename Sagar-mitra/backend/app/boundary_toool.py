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
    pt = Point(lon, lat)
    
    if eez_geoms and not any(geom.contains(pt) for geom in eez_geoms):
        return f"ALERT: [{lat}, {lon}] has crossed into international waters."
        
    if mpa_geoms and any(geom.contains(pt) for geom in mpa_geoms):
        return f"ALERT: [{lat}, {lon}] is inside a Marine Protected Area (MPA)."
        
    return "Coordinate is safely within Indian waters."

if __name__ == "__main__":
    # Test coordinate off Mumbai coast
    print(check_maritime_boundary(18.9, 72.8))