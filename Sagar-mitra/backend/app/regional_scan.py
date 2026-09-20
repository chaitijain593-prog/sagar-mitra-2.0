"""
Sagar Mitra / ORCA - Regional Favorability Scan
====================================================
Answers a class of question nothing else in this codebase can: "which
REGIONS show high chlorophyll and favorable sea surface temperature?"
Every other tool here only ever answers for a single point (wherever the
vessel/query coordinate is) -- this is the first multi-point comparison.

Uses REAL data throughout, not an invented grid:
  1. Today's actual live INCOIS PFZ advisory zones (pfz_tool.get_all_pfz_zones)
     -- these are already analyst/model-identified candidate zones, so
     scanning them is more meaningful than picking arbitrary lat/lon points.
  2. Live chlorophyll + SST for each zone (the same tools the single-point
     path uses).
  3. The already-trained PFZ classifier (pfz_ml.py) to rank them -- ranking
     by the model's own predicted probability is the same "how favorable is
     this combination" question the dashboard's Prediction Telemetry panel
     already answers per-point, just applied across many points at once.

Each zone needs 2 independent external API calls (ocean + chlorophyll).
Fetching zones ONE AT A TIME would multiply that latency by the zone count
(see: why a single point took several seconds earlier). Since these calls
don't depend on each other at all, they run concurrently via a thread pool
-- the same "independent I/O-bound calls" case that makes parallelism a
safe, honest win rather than a premature optimization.
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from app.pfz_tool import get_all_pfz_zones
from app.satellite_tool import get_live_ocean_conditions
from app.chlorophyll_tool import get_chlorophyll_data
from app.pfz_ml import predict_pfz_confidence
from app.data import store as data_store

MAX_ZONES_SCANNED = 12  # keep total concurrent calls considerate of the free public APIs
_SST_RE = re.compile(r"Water Temp:\s*([-\d.]+)")
_CHLOROPHYLL_RE = re.compile(r"Chlorophyll-a:\s*([\d.]+)")


def _evaluate_zone(zone: dict) -> Optional[dict]:
    lat, lon = zone["lat"], zone["lon"]
    ocean_report = get_live_ocean_conditions(lat, lon)
    chlorophyll_report = get_chlorophyll_data(lat, lon)

    sst_match = _SST_RE.search(ocean_report)
    chl_match = _CHLOROPHYLL_RE.search(chlorophyll_report)
    sst = float(sst_match.group(1)) if sst_match else None
    chlorophyll = float(chl_match.group(1)) if chl_match else None

    if sst is None or chlorophyll is None:
        return None  # couldn't get real readings for this zone -- skip it rather than guess

    salinity = data_store.calibrated_clim["sal"]["median"]
    ml_confidence = predict_pfz_confidence(sst, chlorophyll, salinity, lat, lon)

    return {
        "name": zone.get("name") or "Unnamed PFZ",
        "lat": lat, "lon": lon,
        "sst_c": sst,
        "chlorophyll_mgm3": chlorophyll,
        "ml_confidence_pct": ml_confidence,
    }


def scan_favorable_regions(top_n: int = 5) -> List[dict]:
    """
    Returns up to `top_n` of today's real PFZ zones, ranked by the trained
    ML classifier's own PFZ-confidence score. If the model hasn't been
    trained yet (ml_confidence_pct is None for every zone -- see
    pfz_ml.py), ranking falls back to raw chlorophyll instead of silently
    sorting by nothing.
    """
    zones = get_all_pfz_zones()[:MAX_ZONES_SCANNED]
    if not zones:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_evaluate_zone, z) for z in zones]
        for future in as_completed(futures):
            evaluated = future.result()
            if evaluated:
                results.append(evaluated)

    def sort_key(r):
        return r["ml_confidence_pct"] if r["ml_confidence_pct"] is not None else r["chlorophyll_mgm3"] * 100

    results.sort(key=sort_key, reverse=True)
    return results[:top_n]


def format_regional_scan(results: List[dict]) -> str:
    if not results:
        return "Regional Scan: No PFZ zone data available right now to compare regions."

    lines = ["Regional Scan -- top favorable zones today (live PFZ/chlorophyll/SST data):"]
    for i, r in enumerate(results, 1):
        ml_text = (f"{r['ml_confidence_pct']}% ML confidence" if r["ml_confidence_pct"] is not None
                   else "ML confidence unavailable (model not trained)")
        lines.append(
            f"{i}. {r['name']} [{r['lat']}, {r['lon']}] -- "
            f"Chlorophyll-a: {r['chlorophyll_mgm3']} mg/m3, SST: {r['sst_c']}C, {ml_text}."
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_regional_scan(scan_favorable_regions()))
