"""
Sagar Mitra / ORCA - Hazard-Aware Route Planner (A* cost-grid)
===================================================================
Previously the vessel -> nearest-PFZ route only ever tried two fixed
lateral-detour candidates around the direct line and picked whichever
scored better -- not a real search, just "try left, try right".

This module now runs a genuine cost-grid search instead:

  1. Build a lat/lon grid spanning the vessel->target bounding box (plus a
     margin, so a detour has room to route around an obstacle that sits
     near the edge of the direct line).
  2. Price every cell in that grid:
       - MPA occupancy is an exact, free, LOCAL geometry check (reusing the
         same india_mpas.geojson boundary_toool.py already loads) -- a cell
         inside a Marine Protected Area is excluded from the graph
         entirely, since crossing one isn't a cost tradeoff, it's not
         allowed.
       - Wave height is interpolated (inverse-distance weighting) from a
         small grid of REAL live readings fetched once, concurrently, up
         front -- not one live API call per grid cell, which would
         multiply latency by the cell count for no real accuracy gain at
         this coastal scale.
  3. Run A* (admissible haversine-distance heuristic) over that grid to
     find the lowest-cost path from the vessel to the target, instead of
     comparing a handful of hand-picked candidates.
"""
import heapq
import math
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from shapely.geometry import LineString, Point as ShapelyPoint

from app.boundary_toool import mpa_geoms, eez_geoms
from app.marine_weather_tool import get_live_ocean_conditions

WAVE_HAZARD_THRESHOLD_M = 2.5
_WAVE_RE = re.compile(r"Wave Height:\s*([\d.]+)m")

Point = Tuple[float, float]  # (lat, lon)
Cell = Tuple[int, int]       # (row, col) grid index

GRID_SIZE = 16            # 16x16 cost-grid cells spanning the routing bounding box
GRID_MARGIN_DEG = 0.35    # padding around vessel/target so a detour has room to route around an edge obstacle
SAMPLE_GRID = 3           # 3x3 live wave samples used to interpolate cost across the grid (bounded API calls)
HAZARD_CELL_PENALTY = 40.0  # multiplier applied to a step's distance-cost when it lands in >=threshold water
CALM_PREFERENCE = 0.5     # mild extra cost even below threshold, so the search still prefers calmer cells


def _haversine_km(a: Point, b: Point) -> float:
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _sample_wave_height(lat: float, lon: float, day_offset: int = 0,
                         target_hour: Optional[int] = None) -> Optional[float]:
    report = get_live_ocean_conditions(lat, lon, day_offset=day_offset, target_hour=target_hour)
    match = _WAVE_RE.search(report)
    return float(match.group(1)) if match else None


def _point_in_mpa(lat: float, lon: float) -> bool:
    if not mpa_geoms:
        return False
    pt = ShapelyPoint(lon, lat)
    return any(geom.contains(pt) for geom in mpa_geoms)


def _segment_crosses_mpa(a: Point, b: Point) -> bool:
    if not mpa_geoms:
        return False
    line = LineString([(a[1], a[0]), (b[1], b[0])])
    return any(line.intersects(geom) for geom in mpa_geoms)


def _point_outside_eez(lat: float, lon: float) -> bool:
    """True if (lat, lon) is NOT inside any loaded EEZ polygon -- the same
    'crossed into international waters' condition boundary_toool.py's
    check_maritime_boundary already flags, treated here as a hard routing
    obstacle so A* never plans a leg outside Indian waters (Feature 2:
    foreign-EEZ avoidance). If no EEZ data is loaded, nothing is blocked on
    this basis -- matches boundary_toool.py's own fail-open behavior when
    eez_geoms is empty, rather than silently blocking the entire grid."""
    if not eez_geoms:
        return False
    pt = ShapelyPoint(lon, lat)
    return not any(geom.contains(pt) for geom in eez_geoms)


def _segment_crosses_eez_boundary(a: Point, b: Point) -> bool:
    """True if the step from a to b would exit the EEZ. Checked via either
    endpoint being outside it -- sufficient at this grid's cell spacing,
    unlike the small-MPA case _segment_crosses_mpa guards against, since the
    EEZ boundary spans a huge area relative to one grid cell."""
    return _point_outside_eez(*a) or _point_outside_eez(*b)


class _CostGrid:
    """A lat/lon cost grid spanning the vessel->target bounding box. See
    module docstring for how MPA and wave costs are derived."""

    def __init__(self, vessel: Point, target: Point, day_offset: int, target_hour: Optional[int]):
        lat_min = min(vessel[0], target[0]) - GRID_MARGIN_DEG
        lat_max = max(vessel[0], target[0]) + GRID_MARGIN_DEG
        lon_min = min(vessel[1], target[1]) - GRID_MARGIN_DEG
        lon_max = max(vessel[1], target[1]) + GRID_MARGIN_DEG

        self.lat_min, self.lat_max = lat_min, lat_max
        self.lon_min, self.lon_max = lon_min, lon_max
        self.rows, self.cols = GRID_SIZE, GRID_SIZE
        self.lat_step = (lat_max - lat_min) / (self.rows - 1) if self.rows > 1 else 0.0
        self.lon_step = (lon_max - lon_min) / (self.cols - 1) if self.cols > 1 else 0.0

        self.samples: List[Tuple[Point, Optional[float]]] = self._fetch_wave_samples(day_offset, target_hour)
        self._blocked_cache: Dict[Cell, bool] = {}
        self._edge_blocked_cache: Dict[Tuple[Cell, Cell], bool] = {}
        self._wave_cache: Dict[Cell, Optional[float]] = {}

    def _fetch_wave_samples(self, day_offset: int, target_hour: Optional[int]) -> List[Tuple[Point, Optional[float]]]:
        points: List[Point] = []
        for i in range(SAMPLE_GRID):
            for j in range(SAMPLE_GRID):
                lat = self.lat_min + (self.lat_max - self.lat_min) * i / max(SAMPLE_GRID - 1, 1)
                lon = self.lon_min + (self.lon_max - self.lon_min) * j / max(SAMPLE_GRID - 1, 1)
                points.append((lat, lon))

        with ThreadPoolExecutor(max_workers=len(points)) as pool:
            futures = [pool.submit(_sample_wave_height, lat, lon, day_offset, target_hour) for lat, lon in points]
            waves = [f.result() for f in futures]
        return list(zip(points, waves))

    def cell_center(self, row: int, col: int) -> Point:
        return (self.lat_min + row * self.lat_step, self.lon_min + col * self.lon_step)

    def nearest_cell(self, p: Point) -> Cell:
        row = round((p[0] - self.lat_min) / self.lat_step) if self.lat_step else 0
        col = round((p[1] - self.lon_min) / self.lon_step) if self.lon_step else 0
        return max(0, min(self.rows - 1, row)), max(0, min(self.cols - 1, col))

    def wave_at_cell(self, cell: Cell) -> Optional[float]:
        """Inverse-distance-weighted interpolation from the live sample grid."""
        if cell in self._wave_cache:
            return self._wave_cache[cell]
        p = self.cell_center(*cell)
        known = [(pt, w) for pt, w in self.samples if w is not None]
        if not known:
            self._wave_cache[cell] = None
            return None
        weights = [(1.0 / max(_haversine_km(p, pt), 0.05) ** 2) for pt, _ in known]
        total = sum(weights)
        value = sum(w * wt for (_, w), wt in zip(known, weights)) / total
        self._wave_cache[cell] = value
        return value

    def blocked(self, cell: Cell) -> bool:
        if cell not in self._blocked_cache:
            lat, lon = self.cell_center(*cell)
            self._blocked_cache[cell] = _point_in_mpa(lat, lon) or _point_outside_eez(lat, lon)
        return self._blocked_cache[cell]

    def edge_blocked(self, a: Cell, b: Cell) -> bool:
        """Whether the STEP from cell a to cell b crosses an MPA, or would
        exit the EEZ -- checked along the full segment between their
        centers for the MPA case, not just the endpoints, since a small MPA
        (well under one grid cell wide) can sit between two cell centers
        without either one's center falling inside it."""
        key = (a, b) if a <= b else (b, a)
        if key not in self._edge_blocked_cache:
            ca, cb = self.cell_center(*a), self.cell_center(*b)
            self._edge_blocked_cache[key] = (
                _segment_crosses_mpa(ca, cb) or _segment_crosses_eez_boundary(ca, cb)
            )
        return self._edge_blocked_cache[key]

    def move_cost(self, a: Cell, b: Cell) -> float:
        """Cost of stepping from cell a to adjacent cell b."""
        dist = _haversine_km(self.cell_center(*a), self.cell_center(*b))
        wave = self.wave_at_cell(b)
        if wave is not None and wave >= WAVE_HAZARD_THRESHOLD_M:
            dist += dist * HAZARD_CELL_PENALTY * (wave / WAVE_HAZARD_THRESHOLD_M)
        elif wave is not None:
            dist += dist * (wave / WAVE_HAZARD_THRESHOLD_M) * CALM_PREFERENCE
        return dist


_NEIGHBOR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _astar(grid: _CostGrid, start: Cell, goal: Cell) -> Optional[List[Cell]]:
    """Standard 8-directional grid A* with an admissible haversine-distance
    heuristic (never overestimates the true remaining cost, since every
    real step cost is >= its plain distance)."""

    def h(node: Cell) -> float:
        return _haversine_km(grid.cell_center(*node), grid.cell_center(*goal))

    open_heap: List[Tuple[float, float, Cell]] = [(h(start), 0.0, start)]
    came_from: Dict[Cell, Cell] = {}
    g_score: Dict[Cell, float] = {start: 0.0}
    visited: set = set()

    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if current in visited:
            continue
        visited.add(current)
        if current == goal:
            path = [current]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            path.reverse()
            return path

        for dr, dc in _NEIGHBOR_OFFSETS:
            nr, nc = current[0] + dr, current[1] + dc
            if not (0 <= nr < grid.rows and 0 <= nc < grid.cols):
                continue
            neighbor = (nr, nc)
            if neighbor in visited or grid.blocked(neighbor) or grid.edge_blocked(current, neighbor):
                continue
            tentative_g = g + grid.move_cost(current, neighbor)
            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                heapq.heappush(open_heap, (tentative_g + h(neighbor), tentative_g, neighbor))

    return None  # every path to the goal is MPA-blocked


def plan_safe_route(vessel: Point, target: Point, day_offset: int = 0,
                     target_hour: Optional[int] = None) -> dict:
    """
    Returns:
        {
          "waypoints": [[lat, lon], ...],
          "hazard_avoided": bool,
          "max_wave_m": float | None,
          "note": str,
          "samples": [{"lat": float, "lon": float, "wave_m": float|None}, ...],
        }

    `samples` exposes the actual live-sampled points/values the cost grid
    was built from (not just the verdict), so a "Direct" result is visibly
    backed by real numbers rather than looking like a hardcoded default.

    day_offset/target_hour let the wave-hazard cost apply to a FUTURE time
    ("tomorrow morning") instead of only ever checking sea state right now
    -- see marine_weather_tool.get_live_ocean_conditions.
    """
    grid = _CostGrid(vessel, target, day_offset, target_hour)
    start_cell = grid.nearest_cell(vessel)
    goal_cell = grid.nearest_cell(target)

    direct_crosses = _segment_crosses_mpa(vessel, target)
    direct_exits_eez = _segment_crosses_eez_boundary(vessel, target)
    known_samples = [{"lat": p[0], "lon": p[1], "wave_m": w} for p, w in grid.samples]
    direct_max_wave = max((s["wave_m"] for s in known_samples if s["wave_m"] is not None), default=None)

    if grid.blocked(start_cell) or grid.blocked(goal_cell):
        # Vessel or target position itself sits inside an MPA or outside the
        # EEZ -- A* can't route "into" a blocked cell. Fall back to a direct
        # line and let the compliance agent's own boundary alert
        # (boundary_toool.py) carry the actual legal warning rather than
        # silently hiding the point.
        return {
            "waypoints": [list(vessel), list(target)],
            "hazard_avoided": False,
            "max_wave_m": direct_max_wave,
            "note": "Vessel or target position is inside a Marine Protected Area or outside the Indian EEZ -- see compliance alert.",
            "samples": known_samples,
        }

    path_cells = _astar(grid, start_cell, goal_cell)
    if not path_cells:
        return {
            "waypoints": [list(vessel), list(target)],
            "hazard_avoided": False,
            "max_wave_m": direct_max_wave,
            "note": "No EEZ-compliant, MPA-clear path found across the routing grid; showing a direct line. Exercise caution.",
            "samples": known_samples,
        }

    waypoints = [list(vessel)] + [list(grid.cell_center(*c)) for c in path_cells[1:-1]] + [list(target)]
    path_waves = [grid.wave_at_cell(c) for c in path_cells]
    max_wave_on_path = max((w for w in path_waves if w is not None), default=None)
    hazard_avoided = len(waypoints) > 2  # A* found a cheaper path than the straight line

    reasons = []
    if direct_crosses:
        reasons.append("direct line crosses a Marine Protected Area")
    if direct_exits_eez:
        reasons.append("direct line exits the Indian EEZ")
    if direct_max_wave is not None and direct_max_wave >= WAVE_HAZARD_THRESHOLD_M:
        reasons.append(f"direct line passes near {round(direct_max_wave, 2)}m waves")

    if hazard_avoided:
        note = f"A* cost-grid route applied to avoid: {', '.join(reasons) or 'higher-cost cells near the direct line'}."
    else:
        note = "Direct route -- the lowest-cost path across the grid is the straight line (no MPA crossing or hazardous wave cells)."

    return {
        "waypoints": waypoints,
        "hazard_avoided": hazard_avoided,
        "max_wave_m": max_wave_on_path,
        "note": note,
        "samples": known_samples,
    }
