import os
import math
import pandas as pd
import geopandas as gpd

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to calculate great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _query_local_csv(user_lat: float, user_lon: float) -> str:
    """Fallback reader for local pfz_today.csv."""
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, '..', 'data', 'pfz_today.csv')
    
    if not os.path.exists(csv_path):
        return "Both live WebGIS and local pfz_today.csv are unavailable."
    
    df = pd.read_csv(csv_path)
    min_dist = float('inf')
    best_row = None
    
    for _, row in df.iterrows():
        dist = calculate_distance(user_lat, user_lon, float(row['Latitude']), float(row['Longitude']))
        if dist < min_dist:
            min_dist = dist
            best_row = row
            
    if best_row is not None:
        return (f"[Offline Archive Alert] Nearest PFZ is near {best_row['Landing Center']} "
                f"({best_row['State_Sector']}). Coordinates: [{best_row['Latitude']}, {best_row['Longitude']}]. "
                f"Distance: {round(min_dist, 2)} km away.")
    return "No records found in local PFZ dataset."

def get_nearest_pfz(user_lat: float, user_lon: float) -> str:
    """Primary tool: attempts live WebGIS, falls back to local CSV on failure."""
    wfs_url = "https://incois.gov.in/geoserver/wfs?request=GetFeature&service=WFS&version=1.1.0&typeName=incois:pfz_today&outputFormat=application/json"
    
    try:
        pfz_gdf = gpd.read_file(wfs_url)
        min_dist = float('inf')
        nearest_zone = None
        
        for _, row in pfz_gdf.iterrows():
            pt = row.get('geometry')
            if pt:
                dist = calculate_distance(user_lat, user_lon, pt.y, pt.x)
                if dist < min_dist:
                    min_dist = dist
                    nearest_zone = row
                    
        if nearest_zone is not None:
            landing = nearest_zone.get('LandingCenter', nearest_zone.get('landing_center', 'Coast'))
            return f"[Live WebGIS Alert] Nearest PFZ is near {landing}. Distance: {round(min_dist, 2)} km away."
    except Exception:
        pass
        
    return _query_local_csv(user_lat, user_lon)

if __name__ == "__main__":
    # Test with coordinates off Mumbai coast
    print(get_nearest_pfz(18.9, 72.8))