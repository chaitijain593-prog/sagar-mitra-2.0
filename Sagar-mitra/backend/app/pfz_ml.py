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
from typing import Optional, Tuple, Union

import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pfz_predictor_best.joblib")
FEATURE_COLS = ["sst", "chlorophyll", "salinity", "latitude", "longitude"]

_model = None
_load_attempted = False
_load_lock = threading.Lock()

# SHAP explainer, built once against the loaded model's tree classifier
# (see _get_explainer below). Kept separate from _model's load-once lock
# since building the explainer needs the model to already be loaded.
_explainer = None
_explainer_load_attempted = False
_explainer_lock = threading.Lock()

# TreeExplainer only supports tree-based estimators. The training script
# (scripts/train_pfz_model.py) picks whichever of 4 candidate models scores
# highest accuracy, so the saved pipeline's classifier step isn't
# guaranteed to be a tree model -- if it isn't, SHAP attributions are
# reported as unavailable (None) rather than crashing the request.
_TREE_CLASSIFIER_NAMES = {"RandomForestClassifier", "XGBClassifier", "DecisionTreeClassifier",
                           "GradientBoostingClassifier", "ExtraTreesClassifier"}


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


def _get_explainer(model):
    """
    Thread-safe, build-once shap.TreeExplainer accessor -- same
    check-flag-then-lock-then-recheck pattern as _get_model above, and for
    the same reason (a concurrent caller must never observe a half-built
    explainer). Returns None (not an exception) if shap isn't installed or
    the pipeline's classifier step isn't a tree-based estimator, since
    TreeExplainer only supports those.
    """
    global _explainer, _explainer_load_attempted
    if _explainer_load_attempted:
        return _explainer
    with _explainer_lock:
        if _explainer_load_attempted:
            return _explainer
        built = None
        try:
            classifier = model.named_steps["classifier"] if hasattr(model, "named_steps") else model
            classifier_name = type(classifier).__name__
            if classifier_name in _TREE_CLASSIFIER_NAMES:
                import shap
                built = shap.TreeExplainer(classifier)
            else:
                print(f"[pfz_ml] Classifier '{classifier_name}' isn't tree-based -- "
                      f"SHAP TreeExplainer isn't applicable, reporting shap_attributions=None.")
        except Exception as e:
            print(f"[pfz_ml] Failed to build SHAP explainer: {e}")
            built = None
        _explainer = built
        _explainer_load_attempted = True
    return _explainer


def _compute_shap_attributions(model, features: pd.DataFrame, class_index: int) -> Optional[dict]:
    """
    Runs the SHAP explainer on a single already-built feature row and
    returns {"feature_attributions": {feature: value, ...}, "base_value":
    float} for the predicted class, or None if SHAP isn't available for
    this model. `features` must be run through the pipeline's preprocessor
    first (the explainer was built on the raw classifier step, which
    expects already-scaled/imputed input, not the raw feature DataFrame).
    """
    explainer = _get_explainer(model)
    if explainer is None:
        return None
    try:
        preprocessor = model.named_steps.get("preprocessor") if hasattr(model, "named_steps") else None
        transformed = preprocessor.transform(features) if preprocessor is not None else features.values

        raw_shap = explainer.shap_values(transformed)
        # Newer shap versions return one array shaped (n_samples, n_features,
        # n_classes) for a binary/multi-class tree model; older versions
        # return a list of one (n_samples, n_features) array per class.
        # Normalize both to a flat per-feature array for THIS sample/class.
        if isinstance(raw_shap, list):
            sample_shap = raw_shap[class_index][0]
        elif getattr(raw_shap, "ndim", 2) == 3:
            sample_shap = raw_shap[0, :, class_index]
        else:
            sample_shap = raw_shap[0]

        base_value = explainer.expected_value
        if hasattr(base_value, "__len__"):
            base_value = base_value[class_index]

        all_attributions = {
            col: round(float(val), 4) for col, val in zip(features.columns, sample_shap)
        }
        # Top 3 by absolute magnitude -- the strongest drivers of THIS
        # prediction, not every feature (dashboard-facing summary).
        top3 = dict(sorted(all_attributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3])

        return {
            "shap_attributions": top3,
            "feature_attributions": all_attributions,
            "base_value": round(float(base_value), 4),
        }
    except Exception as e:
        print(f"[pfz_ml] SHAP computation failed: {e}")
        return None


def predict_pfz_confidence(
    sst: float, chlorophyll: float, salinity: float, lat: float, lon: float,
    include_shap: bool = False,
) -> Union[Optional[float], Tuple[Optional[float], Optional[dict]]]:
    """
    Returns the trained pipeline's predicted probability (0-100) that this
    coordinate is a Potential Fishing Zone -- the real "ML Confidence Score"
    shown on the ORCA dashboard's Prediction Telemetry panel.

    Returns None if the model hasn't been trained yet, so the caller/UI can
    show that honestly instead of a fabricated number.

    include_shap=False (default, unchanged from before) keeps the original
    contract: a single Optional[float], so every EXISTING caller (main.py's
    _build_telemetry, regional_scan.py's _evaluate_zone) is unaffected.

    include_shap=True returns (confidence, shap_attributions) instead, where
    shap_attributions is {"feature_attributions": {feature: value, ...},
    "base_value": float} -- one SHAP value per input feature, explaining
    this specific prediction -- or None if SHAP isn't available for the
    currently-loaded model (see _get_explainer).
    """
    model = _get_model()
    if model is None:
        return (None, None) if include_shap else None

    features = pd.DataFrame([{
        "sst": sst, "chlorophyll": chlorophyll, "salinity": salinity,
        "latitude": lat, "longitude": lon,
    }])
    proba = model.predict_proba(features)[0]
    classes = list(model.classes_)
    pfz_index = classes.index(1) if 1 in classes else int(proba.argmax())
    confidence = round(float(proba[pfz_index]) * 100, 1)

    if not include_shap:
        return confidence

    shap_attributions = _compute_shap_attributions(model, features, pfz_index)
    return confidence, shap_attributions
