"""
Sagar Mitra - PFZ Predictor Training
=======================================
Trains and compares several classifiers for predicting Potential Fishing
Zones (PFZ) from surface ocean conditions, and exports the best pipeline
for the ORCA backend.

IMPORTANT CONTEXT: there is no verified, INCOIS-sourced "is_pfz" ground
truth available for this project yet. The training data here
(backend/data/pfz_training_data.csv, built by prepare_pfz_dataset.py) uses
a RULE-BASED PROXY label -- see that script's docstring. Any accuracy
number below reflects how well a model can recover a rule we ALREADY KNOW
(chlorophyll + SST/salinity anomaly), not independently discovered fishing
grounds, so it will look artificially strong. That's exactly why
PFZStatisticalValidator (app/statistical_engine.py) exists: instead of
trusting this accuracy figure at face value, it independently re-checks
individual predictions against real conditions with a Z-test and a KS-test.
Step 6 below runs that check against this model's own test-set predictions
as a sanity check before the accuracy number is reported anywhere.

Run once, from the backend/ directory:
    python scripts/train_pfz_model.py
"""
import os
import sys

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.statistical_engine import PFZStatisticalValidator  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pfz_training_data.csv")
# Must match app/pfz_ml.py's MODEL_PATH -- that's where the backend loads it from.
MODEL_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "pfz_predictor_best.joblib")

FEATURE_COLS = ["sst", "chlorophyll", "salinity", "latitude", "longitude"]
TARGET_COL = "is_pfz"


def load_dataset() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run `python scripts/prepare_pfz_dataset.py` "
            f"first to build the labeled training set."
        )
    return pd.read_csv(DATA_PATH)


def train_and_compare(X_train, X_test, y_train, y_test):
    preprocessor = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
        "XGBoost": XGBClassifier(eval_metric="logloss", random_state=42),
        "Support Vector Machine": SVC(probability=True, random_state=42),
    }

    print("--- Model Evaluation Results ---\n")
    best_accuracy, best_model_name, best_pipeline, best_pred = 0.0, "", None, None

    for name, model in models.items():
        clf = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", model)])
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"{name} Accuracy: {acc * 100:.2f}%")
        print(classification_report(y_test, y_pred, zero_division=0))

        if acc > best_accuracy:
            best_accuracy, best_model_name, best_pipeline, best_pred = acc, name, clf, y_pred

    print("--------------------------------")
    print(f"Winning Algorithm: {best_model_name} with {best_accuracy * 100:.2f}% Accuracy\n")
    return best_model_name, best_accuracy, best_pipeline, best_pred


def statistical_grounding_check(X_test: pd.DataFrame, y_pred) -> None:
    """
    Step 6 -- reality-checks the winning model's own test-set predictions
    with PFZStatisticalValidator, instead of taking the accuracy number
    above at face value.
    """
    validator = PFZStatisticalValidator()
    predicted = X_test.copy()
    predicted["predicted_pfz"] = y_pred

    pfz_rows = predicted[predicted["predicted_pfz"] == 1]
    barren_rows = predicted[predicted["predicted_pfz"] == 0]

    print("--- Statistical Grounding Check (Z-Test + KS-Test) ---\n")

    if pfz_rows.empty or barren_rows.empty:
        print("Model predicted only one class on the test set -- cannot run "
              "the grounding check (need both PFZ and barren predictions).")
        return

    # Z-Test: is the mean condition at predicted PFZ points a genuine
    # baseline outlier?
    mean_point = {
        "sst": float(pfz_rows["sst"].mean()),
        "salinity": float(pfz_rows["salinity"].mean()),
        "chlorophyll": float(pfz_rows["chlorophyll"].mean()),
    }
    zscore_results = {
        param: validator.zscore_baseline_check(param, value)
        for param, value in mean_point.items()
    }
    for param, result in zscore_results.items():
        flag = "ANOMALOUS" if result["is_anomalous"] else "within normal range"
        print(f"Z-Test [{param}]: observed={result['observed_value']}, "
              f"z={result['z_score']}, p={result['p_value']} -> {flag}")

    # KS-Test: does chlorophyll inside predicted PFZ points differ from
    # predicted barren points?
    ks_result = validator.ks_distribution_check(
        pfz_rows["chlorophyll"].values, barren_rows["chlorophyll"].values
    )
    differ = "differ significantly" if ks_result["distributions_differ"] else "do NOT differ significantly"
    print(f"\nKS-Test [chlorophyll]: D={ks_result['ks_statistic']}, "
          f"p={ks_result['p_value']} -> PFZ vs. barren distributions {differ}")

    grounded = ks_result["distributions_differ"] and any(r["is_anomalous"] for r in zscore_results.values())
    verdict = "STATISTICALLY GROUNDED" if grounded else "NOT GROUNDED -- treat the accuracy figure with suspicion"
    print(f"\nVerdict: {verdict}")


def main():
    df = load_dataset()
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    best_model_name, best_accuracy, best_pipeline, best_pred = train_and_compare(
        X_train, X_test, y_train, y_test
    )

    statistical_grounding_check(X_test, best_pred)

    joblib.dump(best_pipeline, MODEL_OUTPUT_PATH)
    print(f"\nSaved {best_model_name} pipeline to '{MODEL_OUTPUT_PATH}'")


if __name__ == "__main__":
    main()
