"""
Sagar Mitra / ORCA - Weather Hazard Alerts (Lightning / Cyclone)
====================================================================
Closes the one completely-unstarted item from the ORCA feature audit: the
platform had zero lightning or cyclone coverage. This is a free, keyless
best-effort proxy built on Open-Meteo's forecast endpoint:

  - WMO weather codes 95/96/99 ("thunderstorm", with/without hail) are
    reported as lightning risk.
  - Sustained/gust wind speed at or above gale force (62 km/h, Beaufort 8)
    is reported as a cyclone watch.

The cyclone signal is explicitly a wind-speed heuristic, not an official
IMD/INCOIS cyclone-track bulletin -- there is no free, keyless real-time
cyclone-track API to plug in here, and this module says so in its own
output rather than implying an official warning it can't back up (matching
the honesty pattern the rest of this codebase already uses in
boundary_toool.py and pfz_ml.py).
"""
from datetime import date, timedelta
from typing import Optional

import requests

from app.blackout_cache import cached_get

_THUNDERSTORM_CODES = {95, 96, 99}
CYCLONE_WIND_THRESHOLD_KMH = 62.0  # gale force (Beaufort 8+)


def _build_alert_result(code, wind, gusts, label_prefix: str = "") -> dict:
    """Shared logic: turns a (weather_code, wind_speed, wind_gusts) reading
    into the alert dict, whether that reading came from the "current"
    endpoint or a specific hour of the "hourly" forecast array."""
    lightning = code in _THUNDERSTORM_CODES
    candidates = [v for v in (wind, gusts) if v is not None]
    max_wind = max(candidates) if candidates else None
    cyclone = max_wind is not None and max_wind >= CYCLONE_WIND_THRESHOLD_KMH

    lightning_detail = (
        f"{label_prefix}Thunderstorm activity detected (WMO code {code}) -- lightning risk."
        if lightning else f"{label_prefix}No thunderstorm activity detected."
    )
    cyclone_detail = (
        f"{label_prefix}[Proxy] Sustained/gust wind speed {max_wind:.0f} km/h exceeds gale force -- "
        f"possible cyclonic conditions. This is a wind-speed heuristic, not an official "
        f"IMD/INCOIS cyclone bulletin."
        if cyclone else f"{label_prefix}No gale-force winds detected."
    )
    parts = []
    if lightning:
        parts.append("LIGHTNING RISK")
    if cyclone:
        parts.append("CYCLONE WATCH (wind proxy)")
    summary = " | ".join(parts) if parts else "No lightning or cyclone hazard detected."

    return {
        "lightning_alert": lightning, "lightning_detail": lightning_detail,
        "cyclone_alert": cyclone, "cyclone_detail": cyclone_detail,
        "summary": summary,
    }


def get_weather_hazard_alerts(lat: float, lon: float, day_offset: int = 0,
                               target_hour: Optional[int] = None) -> dict:
    """
    Returns:
        {
          "lightning_alert": bool, "lightning_detail": str,
          "cyclone_alert": bool, "cyclone_detail": str,
          "summary": str,
        }

    day_offset=0 and target_hour=None (the default, and what every existing
    caller gets) checks "current" conditions -- unchanged from before.
    Passing a day_offset > 0 or an explicit target_hour instead checks the
    hourly FORECAST for that day/time, so "any cyclone alerts tomorrow
    morning?" is answered about tomorrow, not right now.
    """
    if day_offset <= 0 and target_hour is None:
        return _get_current_hazard_alerts(lat, lon)
    return _get_forecast_hazard_alerts(lat, lon, max(day_offset, 0), target_hour if target_hour is not None else 8)


def _get_current_hazard_alerts(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current": "weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto",
    }
    try:
        current = cached_get(url, params=params, timeout=10).get("current", {})
        return _build_alert_result(
            current.get("weather_code"), current.get("wind_speed_10m"), current.get("wind_gusts_10m"),
        )
    except requests.exceptions.RequestException as e:
        return {
            "lightning_alert": False, "lightning_detail": f"Network error: {e}",
            "cyclone_alert": False, "cyclone_detail": f"Network error: {e}",
            "summary": "Hazard data unavailable (network error).",
        }


def _get_forecast_hazard_alerts(lat: float, lon: float, day_offset: int, hour: int) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto",
        "forecast_days": min(day_offset + 1, 16),
    }
    target_date = (date.today() + timedelta(days=day_offset)).isoformat()
    label_prefix = f"[Forecast for {target_date} {hour:02d}:00] "
    try:
        hourly = cached_get(url, params=params, timeout=10).get("hourly", {})
        times = hourly.get("time", [])
        target_str = f"{target_date}T{hour:02d}:00"
        if target_str not in times:
            return {
                "lightning_alert": False, "lightning_detail": f"No forecast data available for {target_date}.",
                "cyclone_alert": False, "cyclone_detail": f"No forecast data available for {target_date}.",
                "summary": "Hazard forecast unavailable for that date.",
            }
        idx = times.index(target_str)
        return _build_alert_result(
            hourly.get("weather_code", [])[idx],
            hourly.get("wind_speed_10m", [])[idx],
            hourly.get("wind_gusts_10m", [])[idx],
            label_prefix=label_prefix,
        )
    except requests.exceptions.RequestException as e:
        return {
            "lightning_alert": False, "lightning_detail": f"Network error: {e}",
            "cyclone_alert": False, "cyclone_detail": f"Network error: {e}",
            "summary": "Hazard data unavailable (network error).",
        }


if __name__ == "__main__":
    print(get_weather_hazard_alerts(18.9, 72.8))
    print(get_weather_hazard_alerts(18.9, 72.8, day_offset=1, target_hour=8))
