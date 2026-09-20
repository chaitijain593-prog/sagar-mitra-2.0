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
import requests

_THUNDERSTORM_CODES = {95, 96, 99}
CYCLONE_WIND_THRESHOLD_KMH = 62.0  # gale force (Beaufort 8+)


def get_weather_hazard_alerts(lat: float, lon: float) -> dict:
    """
    Returns:
        {
          "lightning_alert": bool, "lightning_detail": str,
          "cyclone_alert": bool, "cyclone_detail": str,
          "summary": str,
        }
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current": "weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        current = response.json().get("current", {})
        code = current.get("weather_code")
        wind = current.get("wind_speed_10m")
        gusts = current.get("wind_gusts_10m")

        lightning = code in _THUNDERSTORM_CODES
        candidates = [v for v in (wind, gusts) if v is not None]
        max_wind = max(candidates) if candidates else None
        cyclone = max_wind is not None and max_wind >= CYCLONE_WIND_THRESHOLD_KMH

        lightning_detail = (
            f"Thunderstorm activity detected (WMO code {code}) -- lightning risk."
            if lightning else "No thunderstorm activity detected."
        )
        cyclone_detail = (
            f"[Proxy] Sustained/gust wind speed {max_wind:.0f} km/h exceeds gale force -- "
            f"possible cyclonic conditions. This is a wind-speed heuristic, not an official "
            f"IMD/INCOIS cyclone bulletin."
            if cyclone else "No gale-force winds detected."
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
    except requests.exceptions.RequestException as e:
        return {
            "lightning_alert": False, "lightning_detail": f"Network error: {e}",
            "cyclone_alert": False, "cyclone_detail": f"Network error: {e}",
            "summary": "Hazard data unavailable (network error).",
        }


if __name__ == "__main__":
    print(get_weather_hazard_alerts(18.9, 72.8))
