"""
Sagar Mitra - PFZ Training Dataset Builder
=============================================
There is no ready-made "is_pfz" labeled dataset for the Arabian Sea in this
project, so this script builds a defensible PROXY label from data we
actually have:

  1. Surface SST + salinity per historical Argo cast, from the raw CTD
     profile data in backend/data/arabian_sea_cleaned.csv (columns:
     FLOAT_ID, JULD, LATITUDE, LONGITUDE, PRES, TEMP, PSAL).
  2. Chlorophyll-a concentration per unique (lat, lon) grid cell, pulled
     from the live NOAA ERDDAP feed already used by chlorophyll_tool.py.
  3. A rule-based is_pfz label: a point is flagged as a Potential Fishing
     Zone when it shows BOTH strong biological productivity (chlorophyll)
     AND a physical anomaly consistent with upwelling (SST/salinity
     deviating from the dataset's own baseline) -- the same reasoning
     PFZStatisticalValidator (app/statistical_engine.py) uses to
     independently re-check individual ML predictions at inference time.

The classifier trained on this data (see train_pfz_model.py) therefore
learns to approximate a physically grounded rule from raw features, rather
than an arbitrary black-box label.

CAVEAT: chlorophyll comes from TODAY's NOAA monthly composite for every
historical point (there is no historical chlorophyll archive wired up),
so this is a coarse proxy suitable for a prototype/demo, not a
scientifically validated PFZ ground truth. Swap in a real INCOIS PFZ
advisory archive here if/when one becomes available.

Run once, from the backend/ directory:
    python scripts/prepare_pfz_dataset.py
Output:
    backend/data/pfz_training_data.csv
"""
import os
import re
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.chlorophyll_tool import get_chlorophyll_data  # noqa: E402

RAW_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "arabian_sea_cleaned.csv")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "pfz_training_data.csv")

SURFACE_PRES_MAX = 10.0       # dbar; rows shallower than this count as the sea-surface reading
GRID_DEGREES = 0.5            # spatial bin size for chlorophyll lookups (keeps API calls sane)
CHLOROPHYLL_THRESHOLD = 0.2   # mg/m^3; INCOIS's own published PFZ chlorophyll cutoff
ANOMALY_Z_THRESHOLD = 1.0     # |z-score| beyond this counts as a physical anomaly
REQUEST_DELAY_SECONDS = 0.5   # be polite to the shared NOAA ERDDAP endpoint


def _parse_chlorophyll_mg_m3(message: str):
    match = re.search(r"Chlorophyll-a:\s*([\d.]+)", message)
    return float(match.group(1)) if match else None


def build_surface_dataset() -> pd.DataFrame:
    """Collapses each Argo cast down to its shallowest (surface) reading."""
    df = pd.read_csv(RAW_CSV, parse_dates=["JULD"])
    surface = df[df["PRES"] <= SURFACE_PRES_MAX].copy()
    surface = surface.sort_values("PRES").groupby(
        ["FLOAT_ID", "LATITUDE", "LONGITUDE", "JULD"], as_index=False
    ).first()
    surface = surface.rename(columns={
        "LATITUDE": "latitude", "LONGITUDE": "longitude",
        "TEMP": "sst", "PSAL": "salinity",
    })
    return surface[["latitude", "longitude", "sst", "salinity"]].dropna()


def attach_chlorophyll(surface: pd.DataFrame) -> pd.DataFrame:
    """Fetches live chlorophyll once per spatial grid cell, then joins it
    back onto every cast that falls in that cell (instead of one live call
    per row, which would be thousands of redundant NOAA requests)."""
    surface = surface.copy()
    surface["lat_bin"] = (surface["latitude"] / GRID_DEGREES).round() * GRID_DEGREES
    surface["lon_bin"] = (surface["longitude"] / GRID_DEGREES).round() * GRID_DEGREES

    unique_cells = surface[["lat_bin", "lon_bin"]].drop_duplicates().reset_index(drop=True)
    print(f"[prepare_pfz_dataset] Fetching chlorophyll for {len(unique_cells)} unique grid cells...")

    chl_lookup = {}
    for i, cell in unique_cells.iterrows():
        lat, lon = float(cell["lat_bin"]), float(cell["lon_bin"])
        message = get_chlorophyll_data(lat, lon)
        chl_lookup[(lat, lon)] = _parse_chlorophyll_mg_m3(message)
        if (i + 1) % 25 == 0:
            print(f"  ...{i + 1}/{len(unique_cells)} cells done")
        time.sleep(REQUEST_DELAY_SECONDS)

    surface["chlorophyll"] = surface.apply(
        lambda row: chl_lookup.get((row["lat_bin"], row["lon_bin"])), axis=1
    )
    return surface.drop(columns=["lat_bin", "lon_bin"]).dropna(subset=["chlorophyll"])


def label_is_pfz(df: pd.DataFrame) -> pd.DataFrame:
    """Rule-based proxy label: high chlorophyll + a physical SST/salinity
    anomaly vs. the dataset's own baseline (a coarse stand-in for the
    Arabian Sea historical climatology)."""
    df = df.copy()
    sst_mu, sst_sigma = df["sst"].mean(), df["sst"].std() or 1.0
    sal_mu, sal_sigma = df["salinity"].mean(), df["salinity"].std() or 1.0

    sst_z = (df["sst"] - sst_mu) / sst_sigma
    sal_z = (df["salinity"] - sal_mu) / sal_sigma
    physical_anomaly = (sst_z.abs() >= ANOMALY_Z_THRESHOLD) | (sal_z.abs() >= ANOMALY_Z_THRESHOLD)

    df["is_pfz"] = ((df["chlorophyll"] >= CHLOROPHYLL_THRESHOLD) & physical_anomaly).astype(int)
    return df


def main():
    surface = build_surface_dataset()
    print(f"[prepare_pfz_dataset] {len(surface)} surface casts extracted from {RAW_CSV}")

    enriched = attach_chlorophyll(surface)
    labeled = label_is_pfz(enriched)

    labeled.to_csv(OUTPUT_CSV, index=False)
    pfz_rate = labeled["is_pfz"].mean() * 100
    print(f"[prepare_pfz_dataset] Wrote {len(labeled)} rows to {OUTPUT_CSV} "
          f"({pfz_rate:.1f}% labeled as PFZ)")


if __name__ == "__main__":
    main()
