import logging
import requests

logger = logging.getLogger(__name__)

def get_chlorophyll_data(lat: float, lon: float) -> str:
    """Fetches REAL chlorophyll data by taking an area average to bypass point-cloud gaps."""
    
    # Create a 0.5 degree (~50km) bounding box around the coordinate
    lat_min, lat_max = lat - 0.25, lat + 0.25
    lon_min, lon_max = lon - 0.25, lon + 0.25
    
    # Query the monthly composite for the entire bounding box
    url = f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdMH1chlamday.json?chlorophyll[(last)][({lat_min}):({lat_max})][({lon_min}):({lon_max})]"
    
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        rows = data.get("table", {}).get("rows", [])
        
        # Extract only the pixels that are NOT blocked by clouds (not None)
        valid_pixels = [row[3] for row in rows if len(row) >= 4 and row[3] is not None]
        
        if not valid_pixels:
            raise RuntimeError("NOAA CoastWatch returned no unclouded chlorophyll pixels for the requested area.")

        # Average the clear pixels
        avg_chl = sum(valid_pixels) / len(valid_pixels)
        status = "High PFZ Potential" if avg_chl > 0.2 else "Low biological activity"
        
        return f"[Live NOAA Spatial Average] Chlorophyll-a: {round(avg_chl, 3)} mg/m³. {status}."
        
    except requests.exceptions.Timeout as exc:
        logger.warning("NOAA CoastWatch chlorophyll request timed out")
        raise RuntimeError("NOAA CoastWatch chlorophyll service timed out") from exc
    except requests.exceptions.ConnectionError as exc:
        logger.warning("Could not connect to NOAA CoastWatch chlorophyll service")
        raise RuntimeError("NOAA CoastWatch chlorophyll service is unreachable") from exc
    except requests.exceptions.HTTPError as exc:
        logger.warning("NOAA CoastWatch returned an unsuccessful HTTP response: %s", exc)
        raise RuntimeError("NOAA CoastWatch chlorophyll service returned an error") from exc
    except Exception as exc:
        logger.exception("NOAA CoastWatch chlorophyll lookup failed")
        raise RuntimeError(f"NOAA CoastWatch chlorophyll lookup failed: {exc}") from exc

if __name__ == "__main__":
    print(get_chlorophyll_data(15.5, 72.5))
