"""
Sagar Mitra / ORCA - Hazard-Aware Route Planner
===================================================
Previously the vessel -> nearest-PFZ route was a pure client-side straight
line (index.html's plotRoute()), with no awareness of Marine Protected
Areas or sea state. This module computes the route server-side instead:

  1. Check the direct path against real MPA polygons (reusing the same
     india_mpas.geojson boundary_toool.py already loads).
  2. Sample live wave height (satellite_tool.get_live_ocean_conditions)
     along the path. If it crosses an MPA or hazardous (>=2.5m) water,
     try two lateral detour candidates and pick the safer one.

This is a small-candidate-set planner, not a full grid A* -- appropriate
for routing one vessel to one target while keeping live-API call count low
enough to stay responsive in an interactive request.
"""
import re
from typing import List, Optional, Tuple

from shapely.geometry import LineString

from app.boundary_toool import mpa_geoms
from app.satellite_tool import get_live_ocean_conditions

WAVE_HAZARD_THRESHOLD_M = 2.5
_WAVE_RE = re.compile(r"Wave Height:\s*([\d.]+)m")

Point = Tuple[float, float]  # (lat, lon)


def _to_line(points: List[Point]) -> LineString:
    return LineString([(lon, lat) for lat, lon in points])  # shapely wants (x=lon, y=lat)


def _crosses_mpa(points: List[Point]) -> bool:
    if not mpa_geoms:
        return False
    line = _to_line(points)
    return any(line.intersects(geom) for geom in mpa_geoms)


def _sample_wave_height(lat: float, lon: float) -> Optional[float]:
    report = get_live_ocean_conditions(lat, lon)
    match = _WAVE_RE.search(report)
    return float(match.group(1)) if match else None


def _midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _offset_midpoint(a: Point, b: Point, offset_deg: float, side: int) -> Point:
    """A simple perpendicular offset of the path's midpoint, used as a
    single detour waypoint. Not geodesically exact, which is fine at the
    coastal scale this routes over."""
    mid = _midpoint(a, b)
    dlat, dlon = b[0] - a[0], b[1] - a[1]
    perp = (-dlon, dlat)
    length = (perp[0] ** 2 + perp[1] ** 2) ** 0.5 or 1.0
    unit = (perp[0] / length, perp[1] / length)
    return (mid[0] + unit[0] * offset_deg * side, mid[1] + unit[1] * offset_deg * side)


def _score_candidate(points: List[Point]) -> Tuple[float, bool, Optional[float]]:
    """Lower is better. Returns (score, crosses_mpa, max_wave_sampled)."""
    crosses = _crosses_mpa(points)
    waves = [w for w in (_sample_wave_height(lat, lon) for lat, lon in points) if w is not None]
    max_wave = max(waves) if waves else None
    score = (1000.0 if crosses else 0.0) + (max_wave or 0.0)
    return score, crosses, max_wave


def plan_safe_route(vessel: Point, target: Point) -> dict:
    """
    Returns:
        {
          "waypoints": [[lat, lon], ...],   # 2 (direct) or 3 (detour) points
          "hazard_avoided": bool,
          "max_wave_m": float | None,
          "note": str,
          "samples": [{"lat": float, "lon": float, "wave_m": float|None}, ...],
        }

    `samples` exposes the actual live-sampled points/values behind the
    decision (not just the verdict), so a "Direct" result is visibly backed
    by real numbers rather than looking like a hardcoded default.
    """
    direct = [vessel, target]
    direct_crosses = _crosses_mpa(direct)
    direct_mid = _midpoint(vessel, target)
    direct_points = [vessel, direct_mid, target]  # sample start/mid/end for better coverage
    direct_samples = [{"lat": p[0], "lon": p[1], "wave_m": _sample_wave_height(*p)} for p in direct_points]
    direct_max_wave = max((s["wave_m"] for s in direct_samples if s["wave_m"] is not None), default=None)
    needs_detour = direct_crosses or (direct_max_wave is not None and direct_max_wave >= WAVE_HAZARD_THRESHOLD_M)

    if not needs_detour:
        return {
            "waypoints": [list(vessel), list(target)],
            "hazard_avoided": False,
            "max_wave_m": direct_max_wave,
            "note": "Direct route -- no MPA crossing or hazardous wave conditions detected.",
            "samples": direct_samples,
        }

    candidates = []
    for side in (1, -1):
        detour_point = _offset_midpoint(vessel, target, offset_deg=0.6, side=side)
        path = [vessel, detour_point, target]
        score, crosses, max_wave = _score_candidate(path)
        candidates.append((score, path, crosses, max_wave))

    candidates.sort(key=lambda c: c[0])
    _best_score, best_path, best_crosses, best_wave = candidates[0]

    reasons = []
    if direct_crosses:
        reasons.append("direct line crosses a Marine Protected Area")
    if direct_max_wave is not None and direct_max_wave >= WAVE_HAZARD_THRESHOLD_M:
        reasons.append(f"direct line passes through {direct_max_wave}m waves")

    if best_crosses or (best_wave is not None and best_wave >= WAVE_HAZARD_THRESHOLD_M):
        note = (f"Could not find a fully clear detour ({', '.join(reasons)}); showing the "
                f"least-hazardous of the routes tried. Exercise caution.")
    else:
        note = f"Detour applied to avoid: {', '.join(reasons)}."

    return {
        "waypoints": [list(p) for p in best_path],
        "hazard_avoided": True,
        "max_wave_m": best_wave,
        "note": note,
        "samples": direct_samples,
    }
