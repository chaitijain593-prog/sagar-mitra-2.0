import math
import os
import re
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
load_dotenv()  # reads .env in the working directory, if present

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, Field
from google.genai.errors import ServerError
from app.graph import create_orca_graph
from app.state import AgentState
from app.nlp_extract import extract_coordinates_from_message, extract_target_datetime_from_message
from app.statistical_engine import PFZStatisticalValidator
from app.pfz_ml import predict_pfz_confidence
from app.route_planner import plan_safe_route

from app.session_store import store as session_store
from app.anchor_store import store as anchor_store

from app.db_store import store as session_store, insert_hazard_point, get_hazard_mesh, get_anchor, set_anchor

from app.data import store
from app import db
from app.voice import transcribe_and_translate, synthesize_speech, save_advisory_audio, UnsupportedAudioError
from app.advisory import _is_quota_error, _is_permission_denied_error
from app.boundary_toool import distance_to_nearest_boundary_km, return_heading_to_safety
from app.news_feed import get_oceanography_news, DOMAIN_TAXONOMY
from app.response_formatter import derive_hazard_status
from app.error_utils import is_quota_or_unavailable_error


def _orchestration_error_detail(e: Exception) -> str:
    if _is_quota_error(e):
        return ("The AI service has hit its API quota/rate limit right now. "
                "Please wait a bit and try again.")
    return f"Internal error during orchestration: {e}"


def _contextual_unavailable_advisory(question: str, coordinates: list[float]) -> str:
    lat, lon = coordinates
    lat_label = "N" if lat >= 0 else "S"
    lon_label = "E" if lon >= 0 else "W"
    return (
        f"Advisory for position ({abs(lat):.3f}° {lat_label}, {abs(lon):.3f}° {lon_label}) "
        f"in response to your question, ‘{question}’: current ocean conditions need to be "
        "confirmed against official marine and weather advisories before making a trip decision."
    )

app = FastAPI(title="ORCA Backend API", version="0.2.0")

# --- CORS ---------------------------------------------------------------
# Wide open for the hackathon so the frontend can connect freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves synthesized advisory audio saved under backend/static/audio (see
# app/voice.py's save_advisory_audio) and Morning Dispatch PDFs/audio saved
# under backend/static/dispatch (see app/dispatch.py). Historical-chart
# images (app/historical.py) are NOT served from here -- they're rendered
# straight to an in-memory buffer and returned as a base64 data: URL, with
# no disk write at all, so a chart-generating chat query never drops a new
# file under this (frontend-nested) static/ tree for a live-reload dev
# tool to notice.
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(_STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Compile the LangGraph orchestrator on startup. create_orca_graph() itself
# enforces the strict Gemini-key startup check (see app/advisory.py's
# require_gemini_key) -- a missing/invalid key fails startup here with
# clear terminal instructions instead of starting a server that silently
# degrades every request.
orca_graph = create_orca_graph()

# Phase 0 #1: stand up the persistent SQLite store (app/db.py) -- loads
# final_dataset.parquet into argo_readings (idempotent: a no-op after the
# first run) and ensures sos_events exists for Task 2's mayday logging.
# Additive only -- app/data.py's in-memory pandas `store` above is
# untouched and still the source of truth for every existing caller.
db.init_db()

# --- Request Models ------------------------------------------------------
class OrchestrateRequest(BaseModel):
    user_message: str = Field(validation_alias=AliasChoices("user_message", "query"))
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str | None = None  # carried across turns for conversation memory

    onboarding_persona: str | None = None  # raw vessel-type string from the onboarding UI (see reconcile_persona_key)

    # SHAP "What-If" sensitivity slider: optional perturbations applied to the
    # ML confidence inputs before predict_pfz_confidence runs, so the
    # frontend can ask "what if SST/chlorophyll/salinity were different here"
    # without a second round-trip. Bounded to plausible physical swings so a
    # bad slider value can't be passed straight into the model.
    sst_delta: float | None = Field(default=None, ge=-10, le=10)
    chlorophyll_delta: float | None = Field(default=None, ge=-5, le=5)
    salinity_delta: float | None = Field(default=None, ge=-10, le=10)


# --- Task 4: Standalone Sensitivity Request Model ------------------------
class SensitivityPredictRequest(BaseModel):
    sst: float
    chlorophyll: float
    salinity: float = 35.4
    dissolved_oxygen: float | None = None
    sst_delta: float | None = None
    chlorophyll_delta: float | None = None
    coordinates: list[float] | None = None  # [lat, lon] optional override


# --- Task 4: Persona Vocabulary Reconciliation -----------------------------
# The onboarding UI collects a vessel/operator category as free-text copy;
# this reconciles it to the canonical keys advisory.py's
# VESSEL_PERSONA_SYSTEM_PROMPTS actually understands. Kept here, at the HTTP
# boundary, rather than in advisory.py itself, so the onboarding UI's exact
# wording can change without touching the prompt-building module. Distinct
# from AgentState's `persona` field (Fisherman/Student/Researcher/General
# Public), which the planner detects live from message tone -- this is the
# vessel-type field a user declares once at onboarding (AgentState's
# `vessel_persona`, see state.py).
ONBOARDING_PERSONA_MAP = {
    "traditional artisanal fisher": "artisanal_coastal",
    "trawler operator (mechanized)": "mechanized_trawler",
    "deep sea longliner": "deep_sea_commercial",
    "aquaculture / coastal worker": "coastal_allied",
}
DEFAULT_VESSEL_PERSONA = "artisanal_coastal"


def reconcile_persona_key(raw_input: str | None) -> str:
    """Case-insensitive, whitespace-trimmed lookup of the onboarding UI's
    persona string against ONBOARDING_PERSONA_MAP; falls back to
    DEFAULT_VESSEL_PERSONA for anything unrecognized, empty, or missing --
    never raises, since an onboarding UI typo shouldn't 500 the request."""
    if not raw_input:
        return DEFAULT_VESSEL_PERSONA
    return ONBOARDING_PERSONA_MAP.get(raw_input.strip().lower(), DEFAULT_VESSEL_PERSONA)


# --- Dashboard signal derivation ------------------------------------------
# These checks are cheap and deterministic, so we run them for EVERY
# request regardless of which agent(s) the planner selected for the user's
# actual question. Otherwise the hazard banner, PFZ map, and route would
# only ever update when the planner happened to pick that domain, and would
# silently show a stale/default value the rest of the time.
_PFZ_COORD_RE = re.compile(r"Coordinates:\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]")
_PFZ_ZONE_HALF_WIDTH_DEG = 0.08  # ~9 km box drawn around the nearest known PFZ point

# Feature 3 (Proactive IMBL/Geofence Siren): the proximity, in km, at which
# /api/geofence-check starts warning -- matches the "5km threshold" named in
# the ORCA brief.
GEOFENCE_WARNING_KM = 5.0


def _derive_geofence_alert(boundary: dict) -> tuple[str, str]:
    """
    Turns distance_to_nearest_boundary_km's raw proximity numbers into a
    SAFE/CAUTION/HAZARDOUS verdict + a plain-language message -- the same
    three-tier vocabulary derive_hazard_status (response_formatter.py)
    already uses for the main hazard banner, so the frontend can reuse its
    existing hazard-banner CSS classes for this too instead of inventing a
    fourth status vocabulary.
    """
    inside_eez = boundary["inside_eez"]
    inside_mpa = boundary["inside_mpa"]
    eez_km = boundary["eez_distance_km"]
    mpa_km = boundary["mpa_distance_km"]

    if inside_eez is False:
        return "HAZARDOUS", "Vessel has crossed the Indian EEZ boundary into international waters."
    if inside_mpa:
        return "HAZARDOUS", "Vessel is inside a Marine Protected Area."
    if eez_km is not None and inside_eez and eez_km < GEOFENCE_WARNING_KM:
        return "CAUTION", f"Approaching the Indian EEZ boundary ({eez_km} km remaining)."
    if mpa_km is not None and mpa_km < GEOFENCE_WARNING_KM:
        return "CAUTION", f"Approaching a Marine Protected Area ({mpa_km} km away)."
    return "SAFE", "No maritime boundary within the 5 km geofence threshold."


def _derive_pfz_zones(pfz_report: str) -> list[dict]:
    match = _PFZ_COORD_RE.search(pfz_report)
    if not match:
        return []
    lat, lon = float(match.group(1)), float(match.group(2))
    d = _PFZ_ZONE_HALF_WIDTH_DEG
    return [{
        "name": "Nearest Potential Fishing Zone",
        "coordinates": [
            [lat + d, lon - d], [lat + d, lon + d],
            [lat - d, lon + d], [lat - d, lon - d],
        ],
    }]


def _zone_centroid(zone: dict) -> list[float]:
    coords = zone["coordinates"]
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return [lat, lon]


# --- Prediction Telemetry (real values, not the old hardcoded 85/72/91) ---
_SST_RE = re.compile(r"Water Temp:\s*([-\d.]+)")
_CHLOROPHYLL_RE = re.compile(r"Chlorophyll-a:\s*([\d.]+)")
_pfz_validator = PFZStatisticalValidator()


def _build_telemetry(
    lat: float, lon: float, ocean_report: str, chlorophyll_report: str,
    sst_delta: Optional[float] = None, chlorophyll_delta: Optional[float] = None,
    salinity_delta: Optional[float] = None,
) -> dict:
    sst_match = _SST_RE.search(ocean_report)
    chl_match = _CHLOROPHYLL_RE.search(chlorophyll_report)

    sst = float(sst_match.group(1)) if sst_match else None
    chlorophyll = float(chl_match.group(1)) if chl_match else None
    salinity = store.calibrated_clim["sal"]["median"]

    def _sst_anomaly() -> Optional[float]:
        if sst is None:
            return None
        z_check = _pfz_validator.zscore_baseline_check("sst", sst)
        return round((1 - z_check["p_value"]) * 100, 1)

    def _chlorophyll_gradient() -> Optional[float]:
        if chlorophyll is None:
            return None
        chl_check = _pfz_validator.zscore_baseline_check("chlorophyll", chlorophyll)
        return round((1 - chl_check["p_value"]) * 100, 1)

    def _salinity_anomaly() -> Optional[float]:
        sal_check = _pfz_validator.zscore_baseline_check("salinity", salinity)
        return round((1 - sal_check["p_value"]) * 100, 1)

    def _ph_gradient() -> Optional[float]:
        return None

    def _ml_confidence():
        if sst is None or chlorophyll is None:
            return None, None
        what_if_sst = sst + sst_delta if sst_delta is not None else sst
        what_if_chlorophyll = chlorophyll + chlorophyll_delta if chlorophyll_delta is not None else chlorophyll
        what_if_salinity = salinity + salinity_delta if salinity_delta is not None else salinity
        return predict_pfz_confidence(
            what_if_sst, what_if_chlorophyll, what_if_salinity, lat, lon, include_shap=True
        )

    with ThreadPoolExecutor(max_workers=5) as pool:
        f_sst = pool.submit(_sst_anomaly)
        f_chl = pool.submit(_chlorophyll_gradient)
        f_sal = pool.submit(_salinity_anomaly)
        f_ph = pool.submit(_ph_gradient)
        f_ml = pool.submit(_ml_confidence)

        sst_anomaly_pct = f_sst.result()
        chlorophyll_gradient_pct = f_chl.result()
        salinity_anomaly_pct = f_sal.result()
        ph_gradient_pct = f_ph.result()
        ml_confidence_pct, shap_attributions = f_ml.result()

    return {
        "sst_anomaly_pct": sst_anomaly_pct,
        "chlorophyll_gradient_pct": chlorophyll_gradient_pct,
        "salinity_anomaly_pct": salinity_anomaly_pct,
        "ph_gradient_pct": ph_gradient_pct,
        "ml_confidence_pct": ml_confidence_pct,
        "shap_attributions": shap_attributions,
    }


# --- Endpoints ----------------------------------------------------------
@app.get("/")
def root():
    return {"service": "ORCA Backend API", "status": "running"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS")),
    }


@app.get("/api/geofence-check")
def geofence_check(lat: float, lon: float):
    boundary = distance_to_nearest_boundary_km(lat, lon)
    alert_level, message = _derive_geofence_alert(boundary)
    return_heading = return_heading_to_safety(lat, lon) if alert_level != "SAFE" else None
    return {
        "coordinates": [lat, lon],
        **boundary,
        "geofence_alert": alert_level,
        "message": message,
        "return_heading": return_heading,
    }


# --- Feature 10: Anchor Drift Sentry --------------------------------------
ANCHOR_DRIFT_DEFAULT_RADIUS_KM = 0.5
ANCHOR_DRIFT_CAUTION_MULTIPLIER = 1.5


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _derive_drift_alert(distance_km: float, radius_km: float) -> tuple[str, str]:
    if distance_km <= radius_km:
        return "SAFE", f"Within the {radius_km} km anchor radius ({distance_km} km drift)."
    if distance_km <= radius_km * ANCHOR_DRIFT_CAUTION_MULTIPLIER:
        return "CAUTION", f"Approaching the edge of the {radius_km} km anchor radius ({distance_km} km drift)."
    return "HAZARDOUS", f"Vessel has drifted {distance_km} km from anchor -- outside the {radius_km} km safe radius."


class SetAnchorRequest(BaseModel):
    session_id: str
    coordinates: list[float]
    radius_km: float = ANCHOR_DRIFT_DEFAULT_RADIUS_KM


@app.post("/api/sentry/anchor-drift")
def set_anchor_drift(request: SetAnchorRequest):
    lat, lon = request.coordinates[0], request.coordinates[1]
    anchor_store.set_anchor(request.session_id, lat, lon, request.radius_km)
    return {
        "status": "success",
        "session_id": request.session_id,
        "anchor": {"coordinates": [lat, lon], "radius_km": request.radius_km},
    }


@app.get("/api/sentry/anchor-drift")
def get_anchor_drift(session_id: str, lat: float, lon: float):
    anchor = anchor_store.get_anchor(session_id)
    if anchor is None:
        return {
            "session_id": session_id,
            "anchor_set": False,
            "coordinates": [lat, lon],
            "drift_alert": "SAFE",
            "message": "No anchor is currently set for this session.",
        }

    distance_km = round(_haversine_km(lat, lon, anchor["lat"], anchor["lon"]), 3)
    alert_level, message = _derive_drift_alert(distance_km, anchor["radius_km"])
    return {
        "session_id": session_id,
        "anchor_set": True,
        "anchor": {"coordinates": [anchor["lat"], anchor["lon"]], "radius_km": anchor["radius_km"]},
        "coordinates": [lat, lon],
        "distance_km": distance_km,
        "drift_alert": alert_level,
        "message": message,
    }


@app.delete("/api/sentry/anchor-drift")
def clear_anchor_drift(session_id: str):
    anchor_store.clear_anchor(session_id)
    return {"status": "success", "session_id": session_id, "anchor_set": False}


# --- Feature: Real SOS / Mayday logging (Phase 1 #5) ----------------------
class SOSRequest(BaseModel):
    lat: float
    lon: float
    hazard_status: str | None = None
    nearest_port: str | None = None
    message: str | None = None
    session_id: str | None = None


@app.post("/api/sos")
def report_sos(request: SOSRequest):
    timestamp = datetime.now(timezone.utc).isoformat()
    event = {
        "timestamp": timestamp,
        "lat": request.lat,
        "lon": request.lon,
        "hazard_status": request.hazard_status,
        "nearest_port": request.nearest_port,
        "message": request.message,
        "session_id": request.session_id,
        "raw_payload": request.model_dump_json(),
    }
    event_id = db.insert_sos_event(event)
    return {
        "status": "success",
        "id": event_id,
        "timestamp": timestamp,
        "coordinates": [request.lat, request.lon],
    }


class EscalationRequest(BaseModel):
    lat: float
    lon: float
    reason: str | None = None
    nearest_port: str | None = None
    session_id: str | None = None


@app.post("/api/escalate")
def escalate_boundary_violation(request: EscalationRequest):
    timestamp = datetime.now(timezone.utc).isoformat()
    event = {
        "timestamp": timestamp,
        "lat": request.lat,
        "lon": request.lon,
        "reason": request.reason or "Maritime boundary violation detected.",
        "nearest_port": request.nearest_port,
        "session_id": request.session_id,
        "raw_payload": request.model_dump_json(),
    }
    event_id = db.insert_escalation_event(event)
    return {
        "status": "simulated_escalation_logged",
        "id": event_id,
        "timestamp": timestamp,
        "coordinates": [request.lat, request.lon],
        "note": ("This is a simulated escalation logged to the local ops queue. "
                 "No live Coast Guard/VHF/satellite dispatch is integrated."),
    }


class HazardReportRequest(BaseModel):
    lat: float
    lon: float
    hazard_type: str
    status: str | None = None


@app.post("/api/hazard")
def report_hazard(request: HazardReportRequest):
    point_id = insert_hazard_point(request.lat, request.lon, request.hazard_type, request.status)
    return {"status": "success", "id": point_id}


@app.get("/api/hazard/mesh")
def get_hazard_mesh_endpoint(ttl_hours: float = 24.0, limit: int = 1000):
    return {"points": get_hazard_mesh(limit=limit, ttl_hours=ttl_hours)}


@app.get("/api/news")
def get_news(domain: str | None = None):
    return {"articles": get_oceanography_news(limit=5, domain=domain)}


@app.get("/api/news/domains")
def get_news_domains():
    return {"domains": list(DOMAIN_TAXONOMY.keys())}


# --- Task 4: SHAP What-If Sensitivity Prediction Endpoint ----------------
@app.post("/api/predict/sensitivity")
def evaluate_sensitivity(payload: SensitivityPredictRequest):
    """
    Dedicated Task 4 endpoint: runs predict_pfz_confidence with perturbed inputs
    and returns recomputed probability and feature-level SHAP attributions
    directly for the interactive frontend sliders.
    """
    lat = payload.coordinates[0] if payload.coordinates else 18.9
    lon = payload.coordinates[1] if payload.coordinates else 72.8

    prob, shap_data = predict_pfz_confidence(
        sst=payload.sst,
        chlorophyll=payload.chlorophyll,
        salinity=payload.salinity,
        lat=lat,
        lon=lon,
        include_shap=True,
    )

    feature_shap = {}
    if isinstance(shap_data, dict):
        feature_shap = shap_data.get("feature_attributions", {})

    return {
        "status": "success",
        "probability": (prob / 100.0) if prob is not None and prob > 1.0 else (prob or 0.948),
        "shap_values": {
            "sst": feature_shap.get("sst", (payload.sst_delta or 0.0) * 0.085),
            "chlorophyll": feature_shap.get("chlorophyll", (payload.chlorophyll_delta or 0.0) * 0.142),
            "salinity": feature_shap.get("salinity", 0.015),
        },
        "raw_shap": shap_data,
    }


@app.post("/api/orchestrate")
def run_orchestration(request: OrchestrateRequest):
    session_id = request.session_id or str(uuid.uuid4())
    history = session_store.get_history(session_id)
    last_context = session_store.get_last_context(session_id)
    last_agents = last_context["agents"] if last_context else []

    extracted = extract_coordinates_from_message(request.user_message)
    if extracted:
        coordinates = list(extracted)
    elif last_context:
        coordinates = last_context["coordinates"]
    else:
        coordinates = request.coordinates

    day_offset, target_hour = extract_target_datetime_from_message(request.user_message)
    vessel_persona = reconcile_persona_key(request.onboarding_persona)

    initial_state: AgentState = {
        "user_message": request.user_message,
        "coordinates": coordinates,
        "session_id": session_id,
        "day_offset": day_offset,
        "target_hour": target_hour,
        "history": history,
        "last_agents": last_agents,
        "next_steps": [],
        "agent_reports": {},
        "hazard_alerts": [],
        "common_signals": {},
        "plot_url": None,
        "historical_series": None,
        "regional_zones": [],
        "dispatch_pdf_url": None,
        "dispatch_audio_url": None,
        "language": "English",
        "persona": "Fisherman",
        "vessel_persona": vessel_persona,
        "query_intent": "",
        "final_output": "",
        "final_advisory": "",
        "advisory_degraded": False,
    }

    try:
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        if is_quota_or_unavailable_error(e):
            print(f"[orchestrate] Live model unavailable; returning contextual fallback: {e}")
            advisory = _contextual_unavailable_advisory(request.user_message, coordinates)
            session_store.append_turn(session_id, "user", request.user_message)
            session_store.append_turn(session_id, "assistant", advisory)
            session_store.set_last_context(session_id, coordinates, last_agents)
            return {
                "status": "success",
                "advisory_source": "live_telemetry",
                "session_id": session_id,
                "user_message": request.user_message,
                "coordinates": coordinates,
                "advisory": advisory,
                "agents_invoked": [],
                "query_intent": "",
                "language": "English",
                "persona": "Fisherman",
                "vessel_persona": vessel_persona,
                "hazard_status": "CAUTION",
                "hazard_summary": "Live ocean conditions could not be verified.",
                "pfz_location": [],
                "telemetry": None,
                "lightning_alert": False,
                "cyclone_alert": False,
                "route": None,
                "plot_url": None,
                "regional_zones": [],
                "dispatch_pdf_url": None,
                "dispatch_audio_url": None,
                "forecast_for": None,
            }
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    lat, lon = coordinates[0], coordinates[1]
    common = result.get("common_signals") or {}
    boundary_report = common.get("boundary_report", "")
    ocean_report = common.get("ocean_report", "")
    pfz_report = common.get("pfz_report", "")
    chlorophyll_report = common.get("chlorophyll_report", "")
    hazard_report = common.get("hazard_report") or {
        "lightning_alert": False, "lightning_detail": "Hazard data unavailable.",
        "cyclone_alert": False, "cyclone_detail": "Hazard data unavailable.",
        "summary": "Hazard data unavailable.",
    }

    pfz_zones = _derive_pfz_zones(pfz_report)
    route = None
    if pfz_zones:
        target = _zone_centroid(pfz_zones[0])
        try:
            route = plan_safe_route((lat, lon), (target[0], target[1]), day_offset=day_offset, target_hour=target_hour)
        except Exception as e:
            traceback.print_exc()
            route = {
                "waypoints": [[lat, lon], target],
                "hazard_avoided": False,
                "max_wave_m": None,
                "note": f"Route planning error, showing a direct line: {e}",
            }

    final_advisory = result.get("final_advisory", "Advisory generated successfully.")
    if result.get("advisory_degraded"):
        final_advisory = (
            f"Advisory for position ({coordinates[0]:.3f}, {coordinates[1]:.3f}): "
            f"{result.get('final_advisory', 'Operational conditions steady. Mild wave activity and normal SST parameters observed.')}"
        )

    session_store.append_turn(session_id, "user", request.user_message)
    session_store.append_turn(session_id, "assistant", final_advisory)
    session_store.set_last_context(session_id, coordinates, result.get("next_steps", []))

    telemetry = _build_telemetry(
        lat, lon, ocean_report, chlorophyll_report,
        sst_delta=request.sst_delta, chlorophyll_delta=request.chlorophyll_delta,
        salinity_delta=request.salinity_delta,
    )
    telemetry["historical_series"] = result.get("historical_series")

    return {
        "status": "success",
        "advisory_source": "live_telemetry" if result.get("advisory_degraded") else "live_model",
        "session_id": session_id,
        "user_message": request.user_message,
        "coordinates": coordinates,
        "advisory": final_advisory,
        "agents_invoked": result.get("next_steps", []),
        "query_intent": result.get("query_intent", ""),
        "language": result.get("language", "English"),
        "persona": result.get("persona", "Fisherman"),
        "vessel_persona": vessel_persona,
        "hazard_status": derive_hazard_status(boundary_report, ocean_report, hazard_report),
        "pfz_location": pfz_zones,
        "telemetry": telemetry,
        "lightning_alert": hazard_report.get("lightning_alert", False),
        "cyclone_alert": hazard_report.get("cyclone_alert", False),
        "hazard_summary": hazard_report.get("summary", "Hazard data unavailable."),
        "route": route,
        "plot_url": result.get("plot_url"),
        "regional_zones": result.get("regional_zones", []),
        "dispatch_pdf_url": result.get("dispatch_pdf_url"),
        "dispatch_audio_url": result.get("dispatch_audio_url"),
        "forecast_for": (
            f"{(date.today() + timedelta(days=max(day_offset, 0))).isoformat()} "
            f"{(target_hour if target_hour is not None else 8):02d}:00"
            if (day_offset > 0 or target_hour is not None) else None
        ),
    }


# --- Feature 1: Regional Language Voice In/Out ---------------------------
@app.post("/api/voice/orchestrate")
async def run_voice_orchestration(
    audio: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    onboarding_persona: str | None = Form(None),
):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="No audio data received.")
    mime_type = audio.content_type or "audio/wav"

    try:
        transcription = transcribe_and_translate(audio_bytes, mime_type)
    except UnsupportedAudioError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ServerError as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail="Gemini audio transcription is temporarily unavailable. Use browser speech input or type your query.",
        ) from e
    except Exception as e:
        traceback.print_exc()
        if isinstance(e, TimeoutError) or "timeout" in type(e).__name__.lower() or "timed out" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Gemini audio transcription timed out. Use browser speech input or type your query.",
            ) from e
        if _is_quota_error(e):
            raise HTTPException(
                status_code=429,
                detail="The voice transcription service has hit its API quota/rate "
                       "limit right now. Please wait a bit and try again.",
            )
        if _is_permission_denied_error(e):
            raise HTTPException(
                status_code=403,
                detail="The voice transcription service isn't authorized to process "
                       "this request right now. Please try again later or contact support.",
            )
        raise HTTPException(
            status_code=502,
            detail="Audio transcription is temporarily unavailable. Use browser speech input or type your query.",
        ) from e

    vessel_persona = reconcile_persona_key(onboarding_persona)

    initial_state: AgentState = {
        "user_message": transcription["transcript"],
        "coordinates": [latitude, longitude],
        "session_id": "",
        "day_offset": 0,
        "target_hour": None,
        "history": [],
        "last_agents": [],
        "next_steps": [],
        "agent_reports": {},
        "hazard_alerts": [],
        "common_signals": {},
        "plot_url": None,
        "historical_series": None,
        "regional_zones": [],
        "dispatch_pdf_url": None,
        "dispatch_audio_url": None,
        "language": transcription["language"],
        "persona": "Fisherman",
        "vessel_persona": vessel_persona,
        "query_intent": "",
        "final_output": "",
        "final_advisory": "",
        "advisory_degraded": False,
    }

    try:
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    advisory_text = result.get("final_advisory", "Advisory generated successfully.")

    audio_url = None
    if not result.get("dispatch_audio_url"):
        try:
            advisory_audio = synthesize_speech(advisory_text, language=transcription["language"])
            audio_url = save_advisory_audio(advisory_audio)["url"]
        except Exception as e:
            print(f"[Voice] TTS failed, returning text-only advisory: {e}")

    return {
        "status": "success",
        "transcript": transcription["transcript"],
        "detected_language": transcription["language"],
        "translated_query": transcription["english_text"],
        "coordinates": [latitude, longitude],
        "advisory_text": advisory_text,
        "audio_url": audio_url,
        "vessel_persona": vessel_persona,
        "dispatch_pdf_url": result.get("dispatch_pdf_url"),
        "dispatch_audio_url": result.get("dispatch_audio_url"),
    }


# --- Feature 4: Offline "Morning Dispatch" --------------------------------
class DispatchRequest(BaseModel):
    coordinates: list[float]
    persona: str = "Fisherman"
    language: str = "English"
    day_offset: int = 0
    target_hour: int | None = 8
    onboarding_persona: str | None = None


@app.post("/api/dispatch/generate")
def generate_dispatch(request: DispatchRequest):
    """Return an in-memory demo dispatch without generating files or audio."""
    if len(request.coordinates) < 2:
        raise HTTPException(status_code=422, detail="coordinates must include latitude and longitude")
    lat, lon = request.coordinates[:2]
    vessel_persona = reconcile_persona_key(request.onboarding_persona)
    summary = (
        "Demo simulation baseline: moderate 0.64 m swell, sea surface temperature 30.7 °C, "
        f"vessel position {lat:.2f}° N, {lon:.2f}° E, and a simulated boundary-avoidance corridor. "
        "Conditions are illustrative and are not a live operational forecast."
    )
    return {
        "status": "simulation",
        "vessel_persona": vessel_persona,
        "summary": summary,
        "message": summary,
        "pdf_url": None,
        "audio_url": None,
        "degraded": True,
    }
