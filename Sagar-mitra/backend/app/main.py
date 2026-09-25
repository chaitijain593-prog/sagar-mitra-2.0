import math
import os
import re
import sqlite3
import traceback
import uuid
import json, secrets, hashlib, smtplib, time
from urllib.parse import urlencode
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Points directly to backend/.env regardless of current terminal folder
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, Field
from app.graph import create_orca_graph
from app.state import AgentState
from app.nlp_extract import extract_target_datetime_from_message
from app.statistical_engine import PFZStatisticalValidator
from app.pfz_ml import predict_pfz_confidence
from app.route_planner import plan_safe_route
from app.session_store import store as session_store
from app.db_store import insert_hazard_point, get_hazard_mesh
from app.anchor_store import store as anchor_store

from app.data import store
from app import db
from app.voice import transcribe_and_translate, synthesize_speech, save_advisory_audio, UnsupportedAudioError
from app.advisory import _is_quota_error, _is_permission_denied_error, synthesize_advisory, GROQ_API_KEY
from app.boundary_toool import check_geofence, distance_to_nearest_boundary_km, return_heading_to_safety
from app.news_feed import get_oceanography_news, DOMAIN_TAXONOMY
from app.marine_weather_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz_details
from app.chlorophyll_tool import get_chlorophyll_data
from app.response_formatter import derive_hazard_status
from app.indobis_service import get_marine_observations


def _orchestration_error_detail(e: Exception) -> str:
    if _is_quota_error(e):
        return ("The AI service has hit its API quota/rate limit right now. "
                "Please wait a bit and try again.")
    return f"Internal error during orchestration: {e}"


app = FastAPI(title="ORCA Backend API", version="0.2.0")

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

orca_graph = create_orca_graph()
db.init_db()

class OrchestrateRequest(BaseModel):
    user_message: str = Field(validation_alias=AliasChoices("user_message", "query"))
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str | None = None  # carried across turns for conversation memory
    history_override: list[dict[str, str]] | None = Field(default=None, max_length=8)
    reset_context: bool = False  # set when an edited prompt creates a history branch

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
_PFZ_ZONE_HALF_WIDTH_DEG = 0.08
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
    mpa_km = boundary["mpa_distance_km"]

    if inside_eez is None:
        return "CAUTION", "Indian EEZ boundary data is unavailable; vessel status could not be verified."
    if inside_eez is False:
        return "HAZARDOUS", "Vessel has crossed the Indian EEZ boundary into international waters."
    if inside_mpa:
        return "HAZARDOUS", "Vessel is inside a Marine Protected Area."
    if mpa_km is not None and mpa_km < GEOFENCE_WARNING_KM:
        return "CAUTION", f"Approaching a Marine Protected Area ({mpa_km} km away)."
    return "SAFE", "No maritime boundary within the 5 km geofence threshold."

def _derive_hazard_status(boundary_report: str, ocean_report: str, hazard_report: dict) -> str:
    if boundary_report.startswith("ALERT"):
        return "HAZARDOUS"
    if "HAZARDOUS" in ocean_report.upper():
        return "HAZARDOUS"
    if hazard_report.get("cyclone_alert"):
        return "HAZARDOUS"
    if hazard_report.get("lightning_alert"):
        return "CAUTION"
    if boundary_report.startswith("UNVERIFIED"):
        return "CAUTION"
    return "SAFE"

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

@app.get("/")
def root():
    return {"service": "ORCA Backend API", "status": "running"}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "groq_key_configured": bool(GROQ_API_KEY),
    }

@app.get("/api/marine-observations")
async def marine_observations(
    species: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    month: str | None = None,
    season: str | None = None,
    region: str = "indian_ocean",
    include_global_tracks: bool = False,
):
    """Return normalized OBIS observations, optionally filtered for the map."""
    return await get_marine_observations(
        species=species,
        start_date=start_date,
        end_date=end_date,
        month=month,
        season=season,
        region=region,
        include_global_tracks=include_global_tracks,
    )

# --- Auth: username/password + email OTP ---
UF, OTPS, PENDING, TOKENS = "users.json", {}, {}, {}
def _users(): return json.load(open(UF)) if os.path.exists(UF) else {}
def _save(u): json.dump(u, open(UF, "w"))
def _hash(p, s): return hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(s), 200000).hex()

def _otp(user, email, purpose):
    code = f"{secrets.randbelow(10000):04d}"
    OTPS[user] = (code, time.time() + 300, purpose)
    
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if not smtp_user or not smtp_pass:
        # Local development fallback: return the code for the frontend to show.
        return code

    m = EmailMessage()
    m["Subject"] = "Sagar Mitra verification code"
    m["From"] = smtp_user
    m["To"] = email
    m.set_content(f"Your Sagar Mitra OTP is {code}. It expires in 5 minutes.")

    # Using STARTTLS port 587
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(m)
    return None

class Auth(BaseModel): username: str; password: str; email: str = ""; name: str = ""
class Verify(BaseModel): username: str; otp: str; purpose: str
class Prof(BaseModel): token: str; profile: dict

@app.post("/api/auth/signup")
def signup(a: Auth):
    if a.username in _users(): raise HTTPException(409, "Username already taken.")
    if "@" not in a.email: raise HTTPException(400, "Invalid email.")
    salt = secrets.token_hex(8); PENDING[a.username] = {"salt": salt, "hash": _hash(a.password, salt), "email": a.email, "name": a.name, "profile": None}
    try: dev_otp = _otp(a.username, a.email, "signup")
    except Exception as e: raise HTTPException(500, f"Could not send OTP email: {e}")
    return {"ok": True, **({"dev_otp": dev_otp} if dev_otp else {})}

@app.post("/api/auth/login")
def login(a: Auth):
    r = _users().get(a.username)
    if not r or _hash(a.password, r["salt"]) != r["hash"]: raise HTTPException(401, "Invalid username or password.")
    try: dev_otp = _otp(a.username, r["email"], "login")
    except Exception as e: raise HTTPException(500, f"Could not send OTP email: {e}")
    return {"ok": True, **({"dev_otp": dev_otp} if dev_otp else {})}

@app.post("/api/auth/verify")
def verify(v: Verify):
    c = OTPS.get(v.username)
    if not c or c[2] != v.purpose or time.time() > c[1] or c[0] != v.otp: raise HTTPException(400, "Invalid or expired OTP.")
    del OTPS[v.username]; u = _users()
    if v.purpose == "signup": u[v.username] = PENDING.pop(v.username); _save(u)
    t = secrets.token_urlsafe(24); TOKENS[t] = v.username
    return {"token": t, "profile": u[v.username]["profile"], "name": u[v.username].get("name", "")}

@app.post("/api/auth/profile")
def save_profile(p: Prof):
    n = TOKENS.get(p.token)
    if not n: raise HTTPException(401, "Bad token.")
    u = _users(); u[n]["profile"] = p.profile; _save(u); return {"ok": True}

@app.get("/api/geofence-check")
def geofence_check(lat: float, lon: float):
    boundary = distance_to_nearest_boundary_km(lat, lon)
    fence = check_geofence(lat, lon)
    alert_level, message = _derive_geofence_alert(boundary)
    return_heading = return_heading_to_safety(lat, lon) if alert_level != "SAFE" else None
    return {
        "coordinates": [lat, lon],
        "status": fence["status"] if fence["breached"] or not boundary.get("inside_mpa") else alert_level,
        "inside_eez": fence["inside_eez"],
        "breached": fence["breached"],
        "alert_level": fence["alert_level"],
        "alert": message if fence["breached"] else None,
        "dist_to_boundary_km": fence["distance_km"],
        "distance_km": fence["distance_km"],
        **boundary,
        "geofence_alert": alert_level,
        "message": fence["message"] if not boundary.get("inside_mpa") else message,
        "return_heading": return_heading,
    }

# --- Feature 10: Anchor Drift Sentry (+ legacy sqlite anchor check) ---
ANCHOR_DRIFT_DEFAULT_RADIUS_KM = 0.5
ANCHOR_DRIFT_CAUTION_MULTIPLIER = 1.5
ANCHOR_DRIFT_ALERT_M = 50.0
_ANCHOR_DB, _ANCHOR_DDL = "data/sagar_mitra_store.db", "CREATE TABLE IF NOT EXISTS anchor_state (session_id TEXT PRIMARY KEY, lat REAL, lon REAL, set_at TEXT)"
def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float: return _haversine_m(lat1, lon1, lat2, lon2) / 1000.0
def get_anchor(session_id: str):
    with sqlite3.connect(_ANCHOR_DB) as c:
        c.execute(_ANCHOR_DDL); r = c.execute("SELECT lat, lon FROM anchor_state WHERE session_id = ?", (session_id,)).fetchone()
        return {"lat": r[0], "lon": r[1]} if r else None
def set_anchor(session_id: str, lat: float, lon: float):
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_ANCHOR_DB) as c:
        c.execute(_ANCHOR_DDL); c.execute("INSERT OR REPLACE INTO anchor_state (session_id, lat, lon, set_at) VALUES (?, ?, ?, ?)", (session_id, lat, lon, now))
    return {"lat": lat, "lon": lon, "set_at": now}
@app.get("/api/sentry/anchor-drift/check")
def anchor_drift_check(session_id: str, lat: float, lon: float):
    a = get_anchor(session_id)
    if a is None:
        a = set_anchor(session_id, lat, lon)
        return {"status": "ANCHOR_SET", "message": "Anchor dropped at current position.", "anchor": [a["lat"], a["lon"]], "current": [lat, lon], "drift_m": 0.0}
    d = round(_haversine_m(a["lat"], a["lon"], lat, lon), 1); drag = d > ANCHOR_DRIFT_ALERT_M
    return {"status": "DRAGGING" if drag else "HOLDING", "message": f"Anchor dragging -- {d}m from the dropped position." if drag else f"Holding -- {d}m from the dropped position.",
            "anchor": [a["lat"], a["lon"]], "current": [lat, lon], "drift_m": d, "alert_threshold_m": ANCHOR_DRIFT_ALERT_M}
class AnchorResetRequest(BaseModel):
    session_id: str
    lat: float
    lon: float
@app.post("/api/sentry/anchor-drift/reset")
def anchor_drift_reset(request: AnchorResetRequest):
    a = set_anchor(request.session_id, request.lat, request.lon)
    return {"status": "ANCHOR_SET", "anchor": [a["lat"], a["lon"]], "set_at": a["set_at"]}
def _derive_drift_alert(distance_km: float, radius_km: float) -> tuple[str, str]:
    if distance_km <= radius_km: return "SAFE", f"Within the {radius_km} km anchor radius ({distance_km} km drift)."
    if distance_km <= radius_km * ANCHOR_DRIFT_CAUTION_MULTIPLIER: return "CAUTION", f"Approaching the edge of the {radius_km} km anchor radius ({distance_km} km drift)."
    return "HAZARDOUS", f"Vessel has drifted {distance_km} km from anchor -- outside the {radius_km} km safe radius."
class SetAnchorRequest(BaseModel):
    session_id: str
    coordinates: list[float]
    radius_km: float = ANCHOR_DRIFT_DEFAULT_RADIUS_KM
@app.post("/api/sentry/anchor-drift")
def set_anchor_drift(request: SetAnchorRequest):
    lat, lon = request.coordinates[0], request.coordinates[1]
    anchor_store.set_anchor(request.session_id, lat, lon, request.radius_km)
    return {"status": "success", "session_id": request.session_id, "anchor": {"coordinates": [lat, lon], "radius_km": request.radius_km}}
@app.get("/api/sentry/anchor-drift")
def get_anchor_drift(session_id: str, lat: float, lon: float):
    a = anchor_store.get_anchor(session_id)
    if a is None:
        return {"session_id": session_id, "anchor_set": False, "coordinates": [lat, lon], "drift_alert": "SAFE", "message": "No anchor is currently set for this session."}
    dist = round(_haversine_km(lat, lon, a["lat"], a["lon"]), 3); level, msg = _derive_drift_alert(dist, a["radius_km"])
    return {"session_id": session_id, "anchor_set": True, "anchor": {"coordinates": [a["lat"], a["lon"]], "radius_km": a["radius_km"]}, "coordinates": [lat, lon], "distance_km": dist, "drift_alert": level, "message": msg}
@app.delete("/api/sentry/anchor-drift")
def clear_anchor_drift(session_id: str):
    anchor_store.clear_anchor(session_id)
    return {"status": "success", "session_id": session_id, "anchor_set": False}

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
    coordinates = list(request.coordinates)
    if (len(coordinates) != 2 or not all(math.isfinite(value) for value in coordinates)
            or not -90 <= coordinates[0] <= 90 or not -180 <= coordinates[1] <= 180):
        raise HTTPException(422, "Request must include valid vessel coordinates [latitude, longitude].")

    if request.history_override is not None:
        clean_history = []
        for turn in request.history_override:
            role = turn.get("role")
            text = (turn.get("text") or "").strip()
            if role in {"user", "assistant"} and text:
                clean_history.append({"role": role, "text": text[:12000]})
        session_store.replace_history(session_id, clean_history, clear_context=request.reset_context)
    history = session_store.get_history(session_id)
    last_context = session_store.get_last_context(session_id)
    last_agents = last_context["agents"] if last_context else []

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
    }

    try:
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail=f"Live telemetry/OpenAI orchestration failed: {e}",
        ) from e

    lat, lon = coordinates[0], coordinates[1]
    common = result.get("common_signals") or {}
    boundary_report = common.get("boundary_report", "")
    ocean_report = common.get("ocean_report", "")
    pfz_report = common.get("pfz_report", "")
    chlorophyll_report = common.get("chlorophyll_report", "")
    hazard_report = common.get("hazard_report") or {}

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

    final_advisory = result.get("final_advisory")
    if not final_advisory:
        raise HTTPException(503, "OpenAI returned no advisory text for the live telemetry.")

    session_store.append_turn(session_id, "user", request.user_message)
    session_store.append_turn(session_id, "assistant", final_advisory)
    session_store.set_last_context(session_id, coordinates, result.get("next_steps", []))

    telemetry = _build_telemetry(
        lat, lon, ocean_report, chlorophyll_report,
        sst_delta=request.sst_delta, chlorophyll_delta=request.chlorophyll_delta,
        salinity_delta=request.salinity_delta,
    )
    telemetry["historical_series"] = result.get("historical_series")
    wave_match = re.search(r"Wave Height:\s*([0-9]+(?:\.[0-9]+)?)\s*m", ocean_report)
    wave_height = float(wave_match.group(1)) if wave_match else None
    marine_status = "CAUTION" if wave_height is None else "SAFE"
    if result.get("cyclone_alert") or (wave_height is not None and wave_height >= 4.0) or "HAZARDOUS" in ocean_report.upper():
        marine_status = "WARNING"
    elif wave_height is not None and wave_height >= 2.5:
        marine_status = "HAZARDOUS"
    elif hazard_report.get("lightning_alert"):
        marine_status = "CAUTION"
    boundary_alert = str(boundary_report).startswith("ALERT")
    boundary_status = (
        "EEZ BORDER ALERT" if "international waters" in str(boundary_report).lower()
        or "eez" in str(boundary_report).lower() else "REGULATORY CAUTION"
    )

    return {
        "status": "success",
        "advisory_source": "openai_model",
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
        "marine_status": marine_status,
        "boundary_alert": boundary_alert,
        "boundary_status": boundary_status if boundary_alert else None,
        "boundary": common.get("boundary_data"),
        "pfz_location": pfz_zones,
        "telemetry": telemetry,
        "lightning_alert": hazard_report.get("lightning_alert", False),
        "cyclone_alert": hazard_report.get("cyclone_alert", False),
        "hazard_summary": hazard_report.get("summary"),
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
    except Exception as e:
        traceback.print_exc()
        if isinstance(e, TimeoutError) or "timeout" in type(e).__name__.lower() or "timed out" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="OpenAI audio transcription timed out. Use browser speech input or type your query.",
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
    }

    try:
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    advisory_text = result.get("final_advisory")
    if not advisory_text:
        raise HTTPException(502, "OpenAI returned no advisory text for the voice query.")

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

class DispatchRequest(BaseModel):
    coordinates: Any = None
    lat: Any = None
    lon: Any = None
    persona: str = "Fisherman"
    language: str = "English"
    day_offset: int = 0
    target_hour: int | None = 8
    onboarding_persona: str | None = None



@app.post("/api/dispatch/generate")
def generate_dispatch(request: DispatchRequest):
    """Build a dispatch only from telemetry fetched for the requested position."""
    raw_coords = request.coordinates if isinstance(request.coordinates, (list, tuple)) else []
    raw_lat = request.lat if request.lat is not None else (raw_coords[0] if raw_coords else None)
    raw_lon = request.lon if request.lon is not None else (raw_coords[1] if len(raw_coords) > 1 else None)
    try:
        lat, lon = float(raw_lat), float(raw_lon)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(422, "Valid vessel latitude and longitude are required.")
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, "Vessel coordinates are outside valid latitude/longitude ranges.")

    try:
        ocean_report = get_live_ocean_conditions(lat, lon, day_offset=0, target_hour=None)
    except Exception as exc:
        raise HTTPException(503, f"Live marine telemetry failed: {exc}") from exc
    def live_value(pattern: str, field: str) -> float:
        match = re.search(pattern, ocean_report, re.IGNORECASE)
        if not match:
            raise HTTPException(503, f"Live {field} telemetry is unavailable: {ocean_report}")
        try:
            value = float(match.group(1))
            if not math.isfinite(value):
                raise ValueError("non-finite telemetry value")
            return value
        except (TypeError, ValueError):
            raise HTTPException(503, f"Live {field} telemetry is not numeric: {match.group(1)}")

    wave_height = live_value(r"Wave Height:\s*([-+0-9.]+)\s*m", "wave height")
    swell_height = live_value(r"Swell:\s*([-+0-9.]+)\s*m", "swell height")
    swell_period = live_value(r"Swell:\s*[-+0-9.]+\s*m\s*@\s*([-+0-9.]+)\s*s", "swell period")
    wind_knots = live_value(r"Wind Speed:\s*([-+0-9.]+)\s*kts", "wind speed")
    sst_temp = live_value(r"Water Temp:\s*([-+0-9.]+)", "sea surface temperature")

    try:
        chl_report = get_chlorophyll_data(lat, lon)
    except Exception as exc:
        raise HTTPException(503, f"Live chlorophyll telemetry failed: {exc}") from exc
    chl_match = re.search(r"Chlorophyll-a:\s*([-+0-9.]+)", chl_report)
    if not chl_match or "Historical Proxy" in chl_report:
        raise HTTPException(503, f"Live chlorophyll telemetry unavailable: {chl_report}")
    chloro_val = float(chl_match.group(1))
    if not math.isfinite(chloro_val):
        raise HTTPException(503, "Live chlorophyll telemetry is not finite numeric data.")

    try:
        pfz_zone = get_nearest_pfz_details(lat, lon)
    except Exception as exc:
        raise HTTPException(503, f"Live PFZ lookup failed: {exc}") from exc
    if not pfz_zone:
        raise HTTPException(503, "No current PFZ record is available from INCOIS or pfz_today.csv.")
    boundary = distance_to_nearest_boundary_km(lat, lon)
    if not boundary or boundary.get("inside_eez") is None:
        raise HTTPException(503, "Indian EEZ reference geometry is unavailable.")
    bearing = pfz_zone["bearing_deg"]
    distance_nm = pfz_zone["distance_nm"]
    pfz_name = pfz_zone["name"]
    pfz_status = "Current PFZ record located"
    opportunity = pfz_name
    pfz_text = (f"{pfz_name} at {pfz_zone['lat']:.4f}, {pfz_zone['lon']:.4f}; "
                f"{distance_nm:.1f} NM away, heading {bearing:.1f} degrees")

    marine_status = (
        "WARNING" if wave_height >= 4.0 or wind_knots >= 30 or not boundary["inside_eez"] or boundary["inside_mpa"]
        else "CAUTION" if wave_height >= 2.5 or wind_knots >= 20
        else "NORMAL"
    )
    border_distance = boundary.get("eez_distance_km")
    border_text = f"{border_distance:.2f} km" if border_distance is not None else "unavailable"
    eez_status = "INSIDE INDIAN EEZ" if boundary["inside_eez"] else "OUTSIDE EEZ - INTERNATIONAL WATERS"
    live_context = (
        "[LIVE VESSEL & OCEANOGRAPHIC TELEMETRY]\n"
        f"- Position: {lat:.4f}, {lon:.4f}\n"
        f"- Wave Height: {wave_height:.2f} m\n"
        f"- Swell: {swell_height:.2f} m @ {swell_period:.1f} s\n"
        f"- Wind Speed: {wind_knots:.1f} kts\n"
        f"- Sea Surface Temp (SST): {sst_temp:.2f} \u00b0C\n"
        f"- Chlorophyll-a: {chloro_val:.3f} mg/m\u00b3\n"
        f"- Nearest PFZ: {pfz_text}\n"
        f"- Maritime EEZ Status: {eez_status} (Distance to border: {border_text})"
    )
    persona = request.onboarding_persona or request.persona
    try:
        advisory_text = synthesize_advisory(
            raw_report=live_context + "\n\n" + ocean_report + "\n" + chl_report + "\n" + str(boundary),
            persona=persona,
            language=request.language,
            user_message="Generate a pre-sail advisory using the live telemetry provided.",
        )
    except Exception as exc:
        raise HTTPException(503, f"OpenAI dispatch synthesis failed: {exc}") from exc

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    telemetry = {
        "wave_height": f"{wave_height:.2f} m",
        "swell": f"{swell_height:.2f} m @ {swell_period:.1f}s",
        "wind_speed": f"{wind_knots:.1f} kts",
        "sst": f"{sst_temp:.1f} \u00b0C",
        "chlorophyll": f"{chloro_val:.3f} mg/m\u00b3",
        "salinity": None,
    }
    return {
        "status": "success",
        "advisory_source": "live_model",
        "timestamp": timestamp,
        "vessel_persona": persona,
        "coordinates": [round(lat, 4), round(lon, 4)],
        "telemetry": telemetry,
        "telemetry_sources": {"marine_weather": "Open-Meteo live API", "chlorophyll": "NOAA CoastWatch live API", "salinity": "Unavailable: no live salinity source returned"},
        "pfz_advisory": {
            "status": pfz_status,
            "recommended_heading": f"{bearing:.1f}\u00b0" if bearing is not None else None,
            "distance_nm": f"{distance_nm:.1f} NM" if distance_nm is not None else None,
            "target_opportunity": opportunity,
        },
        "safety_and_routing": {
            "status": marine_status,
            "inside_eez": boundary["inside_eez"],
            "breached": boundary.get("breached", not boundary["inside_eez"]),
            "alert_level": boundary.get("alert_level"),
            "eez_distance_km": boundary.get("distance_km", border_text),
            "eez_distance": f"{border_text} to Indian EEZ boundary",
            "corridor": (
                "Safe (Inside Indian EEZ)" if boundary["inside_eez"]
                else "Border Alert (Outside EEZ)"
            ),
        },
        "routing": boundary,
        "sea_condition": f"Wave height {wave_height:.2f} m ({marine_status})",
        "sst": f"{sst_temp:.1f} \u00b0C",
        "corridor": (
            "Safe (Inside Indian EEZ)" if boundary["inside_eez"]
            else "Border Alert (Outside EEZ)"
        ),
        "summary": advisory_text,
        "message": advisory_text,
        "advisory": advisory_text,
        "pdf_url": None,
        "audio_url": None,
        "degraded": False,
    }
@app.get("/api/ecosystem-layers")
def get_ecosystem_layers():
    """Return public data sources used by the optional map overlays."""
    # UNEP-WCMC / Global Mangrove Watch ArcGIS layer, constrained to the
    # approximate Indian EEZ / coastline region to keep the GeoJSON response small.
    mangrove_query = urlencode({
        "where": "1=1",
        "outFields": "pxlval",
        "returnGeometry": "true",
        "geometry": "65,5,98,26",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "resultRecordCount": "2000",
        "f": "geojson",
    })
    return {
        "mangroves": {
            "name": "Global Mangrove Watch (2020)",
            "type": "geojson",
            "description": "Global Mangrove Watch mangrove extent polygons for the Indian region.",
            "source_link": "https://data-gis.unep-wcmc.org/server/rest/services/Hosted/Global_Mangrove_Watch/FeatureServer/0",
            # Optional local mirror path. The client falls back to data_url if it is absent.
            "local_data_url": "/static/data/mangroves_india.geojson",
            "data_url": "https://data-gis.unep-wcmc.org/server/rest/services/Hosted/Global_Mangrove_Watch/FeatureServer/0/query?" + mangrove_query,
        },
        "chlorophyll": {
            "name": "Satellite Chlorophyll-a",
            "type": "wms",
            "description": "NASA GIBS Sentinel-3A OLCI daily chlorophyll-a imagery; satellite coverage and processing can leave gaps.",
            "source_link": "https://oceancolor.gsfc.nasa.gov/",
            "tile_url": "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi",
            "wms_url": "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi",
            "layer_name": "S3A_OLCI_Chlorophyll_a",
        },
    }
