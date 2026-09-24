from datetime import date, timedelta
from typing import Optional

import requests

def get_live_ocean_conditions(lat: float, lon: float, day_offset: int = 0,
                               target_hour: Optional[int] = None) -> str:
    """
    Tool for the AI to fetch waves, temperature, and tides.

    day_offset=0 and target_hour=None (the default, and what every existing
    caller gets) fetches Open-Meteo's "current" reading -- unchanged from
    before. Passing a day_offset > 0 or an explicit target_hour instead
    fetches a genuine hourly FORECAST for that day/time (e.g. "tomorrow
    morning"), rather than silently answering with right-now data for a
    question about the future.
    """
    if day_offset <= 0 and target_hour is None:
        return _get_current_ocean_conditions(lat, lon)
    return _get_forecast_ocean_conditions(lat, lon, max(day_offset, 0), target_hour if target_hour is not None else 8)


def _get_current_ocean_conditions(lat: float, lon: float) -> str:
    url = "https://marine-api.open-meteo.com/v1/marine"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "wave_height,sea_surface_temperature,swell_wave_height,swell_wave_period,sea_level_height_msl",
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
        swell_height = current.get("swell_wave_height")
        swell_period = current.get("swell_wave_period")

        if wave_height is None:
             raise RuntimeError("Marine API returned no wave height for the requested coordinates.")

        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": "wind_speed_10m",
                    "wind_speed_unit": "kn", "timezone": "auto"},
            timeout=10,
        )
        weather_response.raise_for_status()
        weather = weather_response.json()
        wind_knots = (weather.get("current") or {}).get("wind_speed_10m")
        missing = [name for name, value in (
            ("wave height", wave_height), ("swell height", swell_height),
            ("swell period", swell_period), ("wind speed", wind_knots),
            ("sea surface temperature", temp),
        ) if value is None]
        if missing:
            raise RuntimeError("Marine API omitted live telemetry fields: " + ", ".join(missing))
        status = "Safe for navigation" if wave_height < 2.5 else "HAZARDOUS - High Waves"

        return (f"Live conditions at [{lat}, {lon}]: "
                f"Wave Height: {wave_height}m, "
                f"Swell: {swell_height}m @ {swell_period}s, "
                f"Wind Speed: {wind_knots} kts, "
                f"Water Temp: {temp}°C, "
                f"Tide Level (MSL): {tide}m. "
                f"Status: {status}.")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Live marine weather request failed: {e}") from e


def _get_forecast_ocean_conditions(lat: float, lon: float, day_offset: int, hour: int) -> str:
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,sea_surface_temperature,swell_wave_height,swell_wave_period,sea_level_height_msl",
        "timezone": "auto",
        "forecast_days": min(day_offset + 1, 8),  # Open-Meteo marine's supported horizon
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        hourly = response.json().get("hourly", {})
        times = hourly.get("time", [])

        target_date = (date.today() + timedelta(days=day_offset)).isoformat()
        target_str = f"{target_date}T{hour:02d}:00"
        if target_str not in times:
            raise RuntimeError(f"Marine forecast is unavailable for {target_date} {hour:02d}:00 at the requested coordinates.")
        idx = times.index(target_str)

        wave_height = hourly.get("wave_height", [])[idx]
        temp = hourly.get("sea_surface_temperature", [])[idx]
        tide = hourly.get("sea_level_height_msl", [])[idx]
        swell_height = hourly.get("swell_wave_height", [])[idx]
        swell_period = hourly.get("swell_wave_period", [])[idx]

        if wave_height is None:
            raise RuntimeError("Marine API returned no wave forecast at the requested coordinates.")

        wind_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "hourly": "wind_speed_10m",
                    "wind_speed_unit": "kn", "timezone": "auto",
                    "forecast_days": min(day_offset + 1, 8)}, timeout=10,
        )
        wind_response.raise_for_status()
        wind_hourly = wind_response.json().get("hourly", {})
        wind_times = wind_hourly.get("time", [])
        if target_str not in wind_times:
            raise RuntimeError(f"Wind forecast is unavailable for {target_date} {hour:02d}:00.")
        wind_knots = wind_hourly.get("wind_speed_10m", [])[wind_times.index(target_str)]
        missing = [name for name, value in (("water temperature", temp),
                                             ("swell height", swell_height),
                                             ("swell period", swell_period),
                                             ("wind speed", wind_knots)) if value is None]
        if missing:
            raise RuntimeError("Marine forecast omitted fields: " + ", ".join(missing))

        status = "Safe for navigation" if wave_height < 2.5 else "HAZARDOUS - High Waves"

        # Keeps the exact "Wave Height: Xm" / "Water Temp: X°C" tokens the
        # rest of the codebase regex-matches (main.py, route_planner.py) --
        # only the leading label changes to make clear this is a forecast,
        # not a live reading.
        return (f"Forecast for [{lat}, {lon}] on {target_date} {hour:02d}:00: "
                f"Wave Height: {wave_height}m, "
                f"Swell: {swell_height}m @ {swell_period}s, "
                f"Wind Speed: {wind_knots} kts, "
                f"Water Temp: {temp}°C, "
                f"Tide Level (MSL): {tide}m. "
                f"Status: {status}.")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Live marine forecast request failed: {e}") from e


if __name__ == "__main__":
    # Test coordinate in the Arabian Sea
    print(get_live_ocean_conditions(15.5, 72.5))
    print(get_live_ocean_conditions(15.5, 72.5, day_offset=1, target_hour=8))
