import requests

def get_live_ocean_conditions(lat: float, lon: float) -> str:
    """Tool for the AI to fetch live global waves, temperature, and tides."""
    url = "https://marine-api.open-meteo.com/v1/marine"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "wave_height,sea_surface_temperature,sea_level_height_msl",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        wave_height = current.get("wave_height")
        temp = current.get("sea_surface_temperature")
        tide = current.get("sea_level_height_msl")

        if wave_height is None:
             return "Marine data not available (coordinate may be on land)."

        status = "Safe for navigation" if wave_height < 2.5 else "HAZARDOUS - High Waves"

        return (f"Live conditions at [{lat}, {lon}]: "
                f"Wave Height: {wave_height}m, "
                f"Water Temp: {temp}°C, "
                f"Tide Level (MSL): {tide}m. "
                f"Status: {status}.")

    except requests.exceptions.RequestException as e:
        return f"Network error: {e}"

if __name__ == "__main__":
    # Test coordinate in the Arabian Sea
    print(get_live_ocean_conditions(15.5, 72.5))