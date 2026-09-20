"""
Sagar Mitra - PFZ ML Model Loader
====================================
Loads the Random Forest / XGBoost pipeline trained by
backend/scripts/train_pfz_model.py (see that script and
prepare_pfz_dataset.py for how it was built and why its accuracy should be
treated with suspicion until PFZStatisticalValidator confirms it).

This module is intentionally tolerant of the model not existing yet: the
training scripts are a separate, one-time step, so /api/orchestrate must
keep working (with ml_confidence_pct = None) before they've been run.
"""
import os
import threading
from typing import Optional

import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pfz_predictor_best.joblib")

_model = None
_load_attempted = False
_load_lock = threading.Lock()


def _get_model():
    """
    Thread-safe, load-once model accessor. regional_scan.py calls this
    concurrently (one call per zone, via a thread pool).

    IMPORTANT: `_load_attempted` is only set to True AFTER `_model` has
    been fully assigned, and both happen inside the lock. An earlier
    version of this function set the flag first and loaded second -- that
    let a second thread's unlocked fast-path check (`if _load_attempted:`)
    see the flag already flipped (visible the instant the first thread set
    it, lock or no lock) and return `_model` while it was still None,
    because the slow joblib.load() hadn't finished yet. Caught this by
    actually running it under a thread pool: 7 of 8 concurrent callers got
    None even with a lock in place, because the lock was guarding the
    wrong invariant. The cheap unlocked check at the top still keeps the
    common (already-loaded) case lock-free; only the one-time load path
    pays for the lock.
    """
    global _model, _load_attempted
    if _load_attempted:
        return _model
    with _load_lock:
        if _load_attempted:  # someone else finished loading while we waited for the lock
            return _model
        if os.path.exists(MODEL_PATH):
            import joblib
            loaded_model = joblib.load(MODEL_PATH)
        else:
            loaded_model = None
            print(f"[pfz_ml] {MODEL_PATH} not found -- run scripts/prepare_pfz_dataset.py "
                  f"and scripts/train_pfz_model.py to enable the ML Confidence Score. "
                  f"Reporting ml_confidence_pct=None until then.")
        _model = loaded_model
        _load_attempted = True  # only flips True once _model is fully set
    return _model


def predict_pfz_confidence(sst: float, chlorophyll: float, salinity: float,
                            lat: float, lon: float) -> Optional[float]:
    """
    Returns the trained pipeline's predicted probability (0-100) that this
    coordinate is a Potential Fishing Zone -- the real "ML Confidence Score"
    shown on the ORCA dashboard's Prediction Telemetry panel.

    Returns None if the model hasn't been trained yet, so the caller/UI can
    show that honestly instead of a fabricated number.
    """
    model = _get_model()
    if model is None:
        return None

    features = pd.DataFrame([{
        "sst": sst, "chlorophyll": chlorophyll, "salinity": salinity,
        "latitude": lat, "longitude": lon,
    }])
    proba = model.predict_proba(features)[0]
    classes = list(model.classes_)
    pfz_index = classes.index(1) if 1 in classes else int(proba.argmax())
    return round(float(proba[pfz_index]) * 100, 1)
