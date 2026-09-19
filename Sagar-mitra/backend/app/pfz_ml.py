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
from typing import Optional

import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pfz_predictor_best.joblib")

_model = None
_load_attempted = False


def _get_model():
    global _model, _load_attempted
    if not _load_attempted:
        _load_attempted = True
        if os.path.exists(MODEL_PATH):
            import joblib
            _model = joblib.load(MODEL_PATH)
        else:
            print(f"[pfz_ml] {MODEL_PATH} not found -- run scripts/prepare_pfz_dataset.py "
                  f"and scripts/train_pfz_model.py to enable the ML Confidence Score. "
                  f"Reporting ml_confidence_pct=None until then.")
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
