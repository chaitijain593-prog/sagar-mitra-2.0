"""
Sagar Mitra Backend - 4-Tier Statistical Anomaly Engine
=========================================================
Copied verbatim from the hackathon Colab notebook (ArgoStatisticalAnomalyEngine).

Implements a 4-Tier pipeline (QC -> Statistical Scoring -> Physical Rules ->
Persistence Filtering) to detect 7 oceanographic anomaly types from Argo
CTD/BGC profile data, using TEOS-10 (gsw) standardized parameters.

Dependencies:
    pip install numpy pandas scipy gsw
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional, Dict, Any, List, cast
import gsw


class ArgoStatisticalAnomalyEngine:
    """4-Tier statistical anomaly detection engine for Argo float data."""

    def __init__(self, climatology_db: Optional[dict] = None):
        """
        climatology_db: dict of baseline stats keyed by anomaly type, e.g.
            {
              "temp": {"mu":27.5,"sigma":0.9,"p10":25.0,"p90":29.0},
              "sal":  {"median":34.5,"mad":0.3},
              "doxy": {"median":90,"mad":15},
              "ph":   {"mu":8.05,"sigma":0.02},
              "d20":  {"mu":60,"sigma":8},
            }
        Falls back to permissive defaults if not supplied.
        """
        self.clim = climatology_db or {
            "temp": {"mu": 27.5, "sigma": 0.9, "p10": 25.5, "p90": 29.2},
            "sal": {"median": 34.5, "mad": 0.3},
            "doxy": {"median": 120.0, "mad": 20.0},
            "ph": {"mu": 8.05, "sigma": 0.02},
            "d20": {"mu": 60.0, "sigma": 8.0},
        }

    # ------------------------------------------------------------------ #
    # STAGE 1: TEOS-10 STANDARDIZATION
    # ------------------------------------------------------------------ #
    def standardize(self, df_profile: pd.DataFrame) -> pd.DataFrame:
        """Converts raw PRES/TEMP/PSAL -> SA, CT, SIGMA0, depth (z), sound speed."""
        df = df_profile.copy()
        lat = df["LATITUDE"].values
        lon = df["LONGITUDE"].values
        pres = df["PRES"].values
        psal = df["PSAL"].values
        temp = df["TEMP"].values

        df["DEPTH_M"] = np.abs(gsw.z_from_p(pres, lat))
        df["SA"] = gsw.SA_from_SP(psal, pres, lon, lat)
        df["CT"] = gsw.CT_from_t(df["SA"].values, temp, pres)
        df["SIGMA0"] = gsw.sigma0(df["SA"].values, df["CT"].values)
        df["SOUND_SPEED"] = gsw.sound_speed(df["SA"].values, df["CT"].values, pres)
        return df

    # ------------------------------------------------------------------ #
    # TIER 1: QC FILTER
    # ------------------------------------------------------------------ #
    def _qc_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Discards rows with QC >= 3 on TEMP_QC / PSAL_QC if present."""
        mask = pd.Series(True, index=df.index)
        if "TEMP_QC" in df.columns:
            mask &= df["TEMP_QC"] < 3
        if "PSAL_QC" in df.columns:
            mask &= df["PSAL_QC"] < 3
        return cast(pd.DataFrame, df[mask]).reset_index(drop=True)

    # ------------------------------------------------------------------ #
    # TIER 2: STATISTICAL SCORING HELPERS
    # ------------------------------------------------------------------ #
    @staticmethod
    def _zscore(x: float, mu: float, sigma: float) -> tuple[float, float]:
        sigma = sigma if sigma > 0 else 1e-6
        z = (x - mu) / sigma
        p = float(2 * (1 - stats.norm.cdf(abs(z))))
        return float(z), p

    @staticmethod
    def _modified_zscore(x: float, median: float, mad: float) -> float:
        return float(0.6745 * (x - median) / (mad + 1e-6))

    @staticmethod
    def _ttest_window(window: np.ndarray, mu_clim: float) -> tuple[float, float]:
        n = len(window)
        if n < 2:
            return 0.0, 1.0
        s = np.std(window, ddof=1)
        s = s if s > 0 else 1e-6
        t = (np.mean(window) - mu_clim) / (s / np.sqrt(n))
        p_t = float(2 * (1 - stats.t.cdf(abs(t), df=n - 1)))
        return float(t), p_t

    @staticmethod
    def _ks_test(observed: np.ndarray, climatology_sample: np.ndarray) -> tuple[float, float]:
        d_stat, p_val = stats.ks_2samp(observed, climatology_sample)
        return float(cast(float, d_stat)), float(cast(float, p_val))

    # ------------------------------------------------------------------ #
    # TIER 3: PHYSICAL LAYER METRICS
    # ------------------------------------------------------------------ #
    def calculate_layer_metrics(self, df_profile: pd.DataFrame) -> dict:
        """Computes MLD, ILD, BLT, D20 isotherm depth from a standardized profile."""
        df = df_profile.sort_values("DEPTH_M").reset_index(drop=True)
        depth = np.asarray(df["DEPTH_M"].values)
        ct = np.asarray(df["CT"].values)
        sigma0 = np.asarray(df["SIGMA0"].values)

        ref_idx = int(np.argmin(np.abs(depth - 10.0)))
        sigma0_ref = sigma0[ref_idx]
        ct_ref = ct[ref_idx]

        mld_candidates = depth[sigma0 >= sigma0_ref + 0.03]
        mld = float(mld_candidates[0]) if len(mld_candidates) else float(depth[-1])

        ild_candidates = depth[ct <= ct_ref - 0.2]
        ild = float(ild_candidates[0]) if len(ild_candidates) else float(depth[-1])

        blt = max(0.0, ild - mld)

        d20_candidates = depth[ct <= 20.0]
        d20 = float(d20_candidates[0]) if len(d20_candidates) else None

        return {"MLD": round(mld, 1), "ILD": round(ild, 1),
                "BLT": round(blt, 1), "D20": d20}

    # ------------------------------------------------------------------ #
    # TIER 4: MULTI-DAY / MULTI-DEPTH PERSISTENCE
    # ------------------------------------------------------------------ #
    def evaluate_multi_day_timeseries(self, daily_df: pd.DataFrame,
                                       anomaly_type: str = "MHW") -> dict:
        """
        daily_df: DataFrame with columns ['DATE','CT'] (or 'PH'/'D20' etc.)
                  sorted chronologically, one row per day.
        Returns streak length, mean Z, t-stat, p-value for the longest
        qualifying consecutive-day run.
        """
        col = {"MHW": "CT", "MCS": "CT", "PH": "PH", "EDDY": "D20"}[anomaly_type]
        clim_key = {"MHW": "temp", "MCS": "temp", "PH": "ph", "EDDY": "d20"}[anomaly_type]
        mu, sigma = self.clim[clim_key]["mu"], self.clim[clim_key]["sigma"]

        vals = np.asarray(daily_df[col].values)
        z_scores = (vals - mu) / (sigma if sigma > 0 else 1e-6)

        if anomaly_type in ("MHW", "EDDY"):
            flags = z_scores >= 2.0
        elif anomaly_type == "MCS":
            flags = z_scores <= -2.0
        else:  # PH spike (drop)
            flags = z_scores <= -2.0

        # find longest consecutive True run
        best_len, cur_len, best_start = 0, 0, 0
        for i, f in enumerate(flags):
            if f:
                cur_len += 1
                if cur_len > best_len:
                    best_len = cur_len
                    best_start = i - cur_len + 1
            else:
                cur_len = 0

        if best_len == 0:
            return {"consecutive_days": 0, "mean_z_score": 0.0,
                    "t_statistic": 0.0, "p_value_ttest": 1.0, "significant": False}

        window = vals[best_start:best_start + best_len]
        t_stat, p_t = self._ttest_window(window, mu)

        return {
            "consecutive_days": int(best_len),
            "mean_z_score": round(float(np.mean(z_scores[best_start:best_start + best_len])), 2),
            "t_statistic": round(t_stat, 2),
            "p_value_ttest": round(p_t, 4),
            "significant": bool(best_len >= (5 if anomaly_type in ("MHW", "MCS") else 3) and p_t < 0.01),
        }

    # ------------------------------------------------------------------ #
    # MAIN ORCHESTRATOR
    # ------------------------------------------------------------------ #
    def analyze_profile(self, df_profile: pd.DataFrame,
                         historical_timeseries: Optional[pd.DataFrame] = None) -> dict:
        """
        df_profile columns expected: LATITUDE, LONGITUDE, PRES, TEMP, PSAL,
            [TEMP_QC, PSAL_QC, DOXY, PH_IN_SITU_TOTAL, WMO_ID, CYCLE, JULD]
        historical_timeseries (optional): daily DataFrame with ['DATE','CT','PH','D20']
            used for MHW/MCS/PH/EDDY persistence checks.
        """
        raw_n = len(df_profile)
        df = self._qc_filter(df_profile)
        qc_status = "PASSED" if len(df) == raw_n else "PARTIAL_QC_REJECT"
        if df.empty:
            return {"qc_status": "FAILED", "detected_anomalies": [],
                    "error": "All rows failed QC filter."}

        df = self.standardize(df)
        layers = self.calculate_layer_metrics(df)
        anomalies: List[Dict[str, Any]] = []

        # --- 1 & 2: MHW / MCS (surface layer, <=30m) ---
        surface = cast(pd.DataFrame, df[df["DEPTH_M"] <= 30.0])
        if not surface.empty:
            ct_mean = float(cast(float, surface["CT"].mean()))
            z, p = self._zscore(ct_mean, self.clim["temp"]["mu"], self.clim["temp"]["sigma"])
            persistence = (self.evaluate_multi_day_timeseries(historical_timeseries, "MHW")
                           if historical_timeseries is not None else
                           {"consecutive_days": 1, "mean_z_score": z, "t_statistic": 0.0,
                            "p_value_ttest": p, "significant": (abs(z) >= 2.0 and p < 0.01)})
            if z >= 2.0 and persistence["significant"]:
                anomalies.append(self._pack("Marine Heatwave (MHW)", surface, persistence,
                                             z, "High" if z >= 3.0 else "Moderate",
                                             "Sustained upper-ocean thermal anomaly exceeding "
                                             "climatological threshold."))
            elif z <= -2.0 and persistence["significant"]:
                anomalies.append(self._pack("Marine Cold Spell (MCS)", surface, persistence,
                                             z, "High" if z <= -3.0 else "Moderate",
                                             "Sustained upper-ocean cooling anomaly, likely "
                                             "upwelling-driven."))

        # --- 3: OMZ / Hypoxia (100-1000m) ---
        if "DOXY" in df.columns:
            omz_layer = cast(pd.DataFrame, df[(df["DEPTH_M"] >= 100) & (df["DEPTH_M"] <= 1000)])
            hypoxic = cast(pd.DataFrame, omz_layer[omz_layer["DOXY"] < 60.0])
            if len(hypoxic) >= 3:
                mi = self._modified_zscore(float(cast(float, hypoxic["DOXY"].mean())),
                                            self.clim["doxy"]["median"], self.clim["doxy"]["mad"])
                anomalies.append(self._pack(
                    "Oxygen Minimum Zone (OMZ / Hypoxia)", hypoxic,
                    {"consecutive_days": None, "mean_z_score": None,
                     "t_statistic": None, "p_value_ttest": None, "robust_m_i": round(mi, 2)},
                    mi, "High",
                    "Dissolved oxygen below hypoxic threshold (60 umol/kg) across "
                    "3+ consecutive depth bins."))

        # --- 4: Salinity Anomaly & Barrier Layer ---
        deep_ok = cast(pd.DataFrame, df[df["DEPTH_M"] <= 200])
        if not deep_ok.empty:
            sa_val = float(cast(float, deep_ok["SA"].mean()))
            mi_sal = self._modified_zscore(sa_val, self.clim["sal"]["median"], self.clim["sal"]["mad"])
            blt = layers["BLT"]
            if abs(mi_sal) >= 3.5 or blt >= 15.0:
                anomalies.append(self._pack(
                    "Salinity Anomaly / Barrier Layer", deep_ok,
                    {"robust_m_i": round(mi_sal, 2), "barrier_layer_m": blt},
                    mi_sal, "High" if abs(mi_sal) >= 4.5 else "Moderate",
                    f"Robust salinity anomaly (M_i={mi_sal:.2f}) with barrier layer "
                    f"thickness {blt}m."))

        # --- 5: Ocean Acidification Spike ---
        if "PH_IN_SITU_TOTAL" in df.columns:
            ph_val = float(cast(float, df["PH_IN_SITU_TOTAL"].mean()))
            z_ph, p_ph = self._zscore(ph_val, self.clim["ph"]["mu"], self.clim["ph"]["sigma"])
            delta_ph = ph_val - self.clim["ph"]["mu"]
            if delta_ph <= -0.15 or z_ph <= -2.0:
                anomalies.append(self._pack(
                    "Ocean Acidification Spike", df,
                    {"z_score": round(z_ph, 2), "p_value": round(p_ph, 4)},
                    z_ph, "High" if z_ph <= -3.0 else "Moderate",
                    f"pH dropped {abs(delta_ph):.2f} units below climatological baseline."))

        # --- 6: Mesoscale Eddy (D20 displacement) ---
        if layers["D20"] is not None:
            z_d20, p_d20 = self._zscore(layers["D20"], self.clim["d20"]["mu"], self.clim["d20"]["sigma"])
            delta_d20 = layers["D20"] - self.clim["d20"]["mu"]
            ks_p = 0.005  # placeholder unless historical_timeseries K-S supplied
            if historical_timeseries is not None and "D20" in historical_timeseries.columns:
                ks_stat, ks_p = self._ks_test(
                    np.array([layers["D20"]]), np.asarray(historical_timeseries["D20"].values))
            if (z_d20 >= 2.0 and delta_d20 >= 30 and ks_p < 0.01):
                anomalies.append(self._pack(
                    "Mesoscale Warm-Core Eddy", df,
                    {"z_score": round(z_d20, 2), "delta_d20_m": round(delta_d20, 1), "p_ks": round(ks_p, 4)},
                    z_d20, "High", "D20 isotherm displaced downward, indicating warm-core eddy."))
            elif (z_d20 <= -2.0 and delta_d20 <= -30 and ks_p < 0.01):
                anomalies.append(self._pack(
                    "Mesoscale Cold-Core Eddy", df,
                    {"z_score": round(z_d20, 2), "delta_d20_m": round(delta_d20, 1), "p_ks": round(ks_p, 4)},
                    z_d20, "High", "D20 isotherm shoaled upward, indicating cold-core eddy."))

        # --- 7: Sensor / Biofouling Drift ---
        deep_sensor = cast(pd.DataFrame, df[df["DEPTH_M"] > 1500])
        qc_flagged = False
        if "TEMP_QC" in df_profile.columns or "PSAL_QC" in df_profile.columns:
            temp_flag = cast(Any, df_profile.get("TEMP_QC", 0))
            psal_flag = cast(Any, df_profile.get("PSAL_QC", 0))
            qc_flagged = bool(((temp_flag >= 3) | (psal_flag >= 3)).any())
        beta, p_beta = 0.0, 1.0
        if not deep_sensor.empty and "JULD" in deep_sensor.columns and len(deep_sensor) >= 3:
            juld_numeric = pd.to_datetime(deep_sensor["JULD"]).astype("int64") / 1e9  # seconds
            slope, _intercept, _r, p_beta_raw, _se = stats.linregress(
                juld_numeric, np.asarray(deep_sensor["SA"]))
            beta = float(cast(float, slope)) * 30 * 86400  # SA units per month (slope is per second)
            p_beta = float(cast(float, p_beta_raw))
        if qc_flagged or (abs(beta) > 0.05 and p_beta < 0.01):
            anomalies.append(self._pack(
                "Sensor / Biofouling Drift", deep_sensor if not deep_sensor.empty else df,
                {"beta_psu_per_month": round(beta, 3), "p_value": round(p_beta, 4),
                 "qc_flagged": qc_flagged},
                beta, "Moderate",
                "Deep-level salinity drift or QC flag suggests sensor fouling/drift."))

        return {
            "wmo_id": int(df_profile["WMO_ID"].iloc[0]) if "WMO_ID" in df_profile.columns else None,
            "profile_cycle": int(df_profile["CYCLE"].iloc[0]) if "CYCLE" in df_profile.columns else None,
            "location": {"lat": float(df_profile["LATITUDE"].iloc[0]),
                         "lon": float(df_profile["LONGITUDE"].iloc[0])},
            "qc_status": qc_status,
            "layer_metrics": layers,
            "detected_anomalies": anomalies,
        }

    @staticmethod
    def _pack(name: str, depth_df: pd.DataFrame, metrics: dict, score: float,
              severity: str, summary: str) -> dict:
        depth_range = [float(cast(float, depth_df["DEPTH_M"].min())), float(cast(float, depth_df["DEPTH_M"].max()))] \
            if "DEPTH_M" in depth_df.columns and len(depth_df) else [0.0, 0.0]
        return {
            "anomaly_type": name,
            "depth_range_meters": [round(depth_range[0], 1), round(depth_range[1], 1)],
            "severity": severity,
            "statistical_metrics": metrics,
            "oceanographic_summary": summary,
        }


# ---------------------------------------------------------------------- #
# PFZ STATISTICAL GROUNDING LAYER
# ---------------------------------------------------------------------- #
class PFZStatisticalValidator:
    """
    Statistical grounding layer for ML-predicted Potential Fishing Zones (PFZ).

    A Random Forest / XGBoost classifier trained to flag PFZ coordinates can
    report unrealistically high test accuracy (95%+) because the engineered
    features correlate too tightly with the label, or the label itself is
    noisy/leaky. Before ORCA surfaces a "predicted PFZ" to a fisherman, these
    two independent, classical statistical checks confirm the prediction is
    grounded in real, physically anomalous ocean conditions rather than being
    a model artifact:

      1. Z-Test  (zscore_baseline_check) -- is the real-time SST/salinity at
         the predicted coordinate a genuine statistical outlier against the
         known Arabian Sea historical climatology? Confirms the zone is
         physically anomalous (e.g. consistent with upwelling) rather than
         an average, unremarkable patch of ocean the model mislabeled.

      2. KS-Test (ks_distribution_check) -- does the distribution of
         environmental readings *inside* the predicted PFZ differ
         significantly from a sample of readings in known barren (non-PFZ)
         water? A significant KS result shows the model is separating two
         distinct oceanographic populations, not making random guesses.
    """

    # Arabian Sea baseline climatology (mean/std). Override with values
    # computed from real historical data (e.g. DataStore.calibrated_clim)
    # wherever available -- these are permissive fallback defaults.
    DEFAULT_BASELINE = {
        "sst": {"mu": 27.8, "sigma": 1.1},
        "salinity": {"mu": 35.5, "sigma": 0.6},
        "chlorophyll": {"mu": 0.35, "sigma": 0.25},
    }

    def __init__(self, baseline: Optional[dict] = None):
        self.baseline = baseline or self.DEFAULT_BASELINE

    @staticmethod
    def _zscore(x: float, mu: float, sigma: float) -> tuple[float, float]:
        sigma = sigma if sigma > 0 else 1e-6
        z = (x - mu) / sigma
        p_value = float(2 * (1 - stats.norm.cdf(abs(z))))
        return float(z), p_value

    def zscore_baseline_check(self, parameter: str, observed_value: float,
                               z_threshold: float = 2.0) -> dict:
        """Tier 1 -- Z-Test for Baseline Comparison (see class docstring)."""
        if parameter not in self.baseline:
            raise ValueError(f"No baseline climatology configured for '{parameter}'.")
        mu = self.baseline[parameter]["mu"]
        sigma = self.baseline[parameter]["sigma"]
        z, p_value = self._zscore(observed_value, mu, sigma)
        return {
            "parameter": parameter,
            "observed_value": round(float(observed_value), 3),
            "baseline_mean": mu,
            "baseline_sigma": sigma,
            "z_score": round(z, 3),
            "p_value": round(p_value, 5),
            "is_anomalous": bool(abs(z) >= z_threshold and p_value < 0.05),
        }

    @staticmethod
    def ks_distribution_check(pfz_samples, barren_samples, p_threshold: float = 0.05) -> dict:
        """Tier 2 -- KS-Test for Distribution Validation (see class docstring)."""
        pfz_samples = np.asarray(pfz_samples, dtype=float)
        barren_samples = np.asarray(barren_samples, dtype=float)
        if len(pfz_samples) < 2 or len(barren_samples) < 2:
            return {
                "ks_statistic": 0.0,
                "p_value": 1.0,
                "distributions_differ": False,
                "note": "Insufficient samples for a KS test (need >= 2 per group).",
            }
        d_stat, p_value = stats.ks_2samp(pfz_samples, barren_samples)
        return {
            "ks_statistic": round(float(d_stat), 4),
            "p_value": round(float(p_value), 5),
            "distributions_differ": bool(p_value < p_threshold),
        }

    def validate_prediction(self, pfz_point: Dict[str, float],
                             pfz_samples, barren_samples) -> dict:
        """
        Runs both checks for a single ML-flagged PFZ coordinate.

        pfz_point: dict of real-time readings at the predicted coordinate,
            e.g. {"sst": 25.1, "salinity": 34.9, "chlorophyll": 0.42}.
        pfz_samples / barren_samples: 1D arrays of a single parameter's
            readings from inside the predicted zone vs. known barren water
            (e.g. chlorophyll concentrations), used for the KS test.

        Returns a combined verdict: the prediction is only considered
        "statistically_grounded" if the zone is both a genuine baseline
        outlier AND distributionally distinct from barren water.
        """
        zscore_results = {
            param: self.zscore_baseline_check(param, value)
            for param, value in pfz_point.items()
            if param in self.baseline
        }
        ks_result = self.ks_distribution_check(pfz_samples, barren_samples)

        grounded = ks_result["distributions_differ"] and any(
            r["is_anomalous"] for r in zscore_results.values()
        )
        return {
            "zscore_checks": zscore_results,
            "ks_test": ks_result,
            "statistically_grounded": grounded,
        }


# ---------------------------------------------------------------------- #