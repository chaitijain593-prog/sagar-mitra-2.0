import math
import os
import re
import traceback
import uuid
import json, secrets, hashlib, smtplib, time
from email.message import EmailMessage
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Points directly to backend/.env regardless of current terminal folder
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.graph import create_orca_graph
from app.state import AgentState
from app.nlp_extract import extract_coordinates_from_message, extract_target_datetime_from_message
from app.statistical_engine import PFZStatisticalValidator
from app.pfz_ml import predict_pfz_confidence
from app.route_planner import plan_safe_route
from app.db_store import store as session_store, insert_hazard_point, get_hazard_mesh, get_anchor, set_anchor
from app.data import store
from app import db
from app.voice import transcribe_and_translate, synthesize_speech, save_advisory_audio, UnsupportedAudioError
from app.advisory import _is_quota_error, _is_permission_denied_error
from app.boundary_toool import distance_to_nearest_boundary_km, return_heading_to_safety
from app.dispatch import generate_morning_dispatch
from app.news_feed import get_oceanography_news, DOMAIN_TAXONOMY


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

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(_STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

orca_graph = create_orca_graph()
db.init_db()

class OrchestrateRequest(BaseModel):
    user_message: str
    coordinates: list[float]
    session_id: str | None = None
    sst_delta: float | None = Field(default=None, ge=-10, le=10)
    chlorophyll_delta: float | None = Field(default=None, ge=-5, le=5)
    salinity_delta: float | None = Field(default=None, ge=-10, le=10)

_PFZ_COORD_RE = re.compile(r"Coordinates:\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]")
_PFZ_ZONE_HALF_WIDTH_DEG = 0.08
GEOFENCE_WARNING_KM = 5.0

def _derive_geofence_alert(boundary: dict) -> tuple[str, str]:
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
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS")),
    }

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
        raise RuntimeError("SMTP credentials missing in environment (SMTP_USER/SMTP_PASS).")

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

class Auth(BaseModel): username: str; password: str; email: str = ""; name: str = ""
class Verify(BaseModel): username: str; otp: str; purpose: str
class Prof(BaseModel): token: str; profile: dict

@app.post("/api/auth/signup")
def signup(a: Auth):
    if a.username in _users(): raise HTTPException(409, "Username already taken.")
    if "@" not in a.email: raise HTTPException(400, "Invalid email.")
    salt = secrets.token_hex(8); PENDING[a.username] = {"salt": salt, "hash": _hash(a.password, salt), "email": a.email, "name": a.name, "profile": None}
    try: _otp(a.username, a.email, "signup")
    except Exception as e: raise HTTPException(500, f"Could not send OTP email: {e}")
    return {"ok": True}

@app.post("/api/auth/login")
def login(a: Auth):
    r = _users().get(a.username)
    if not r or _hash(a.password, r["salt"]) != r["hash"]: raise HTTPException(401, "Invalid username or password.")
    try: _otp(a.username, r["email"], "login")
    except Exception as e: raise HTTPException(500, f"Could not send OTP email: {e}")
    return {"ok": True}

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
    alert_level, message = _derive_geofence_alert(boundary)
    return_heading = return_heading_to_safety(lat, lon) if alert_level != "SAFE" else None
    return {
        "coordinates": [lat, lon],
        **boundary,
        "geofence_alert": alert_level,
        "message": message,
        "return_heading": return_heading,
    }

ANCHOR_DRIFT_ALERT_M = 50.0

def get_anchor(session_id: str):
    with sqlite3.connect("data/sagar_mitra_store.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS anchor_state (session_id TEXT PRIMARY KEY, lat REAL, lon REAL, set_at TEXT)")
        row = conn.execute("SELECT lat, lon FROM anchor_state WHERE session_id = ?", (session_id,)).fetchone()
        return {"lat": row[0], "lon": row[1]} if row else None

def set_anchor(session_id: str, lat: float, lon: float):
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect("data/sagar_mitra_store.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS anchor_state (session_id TEXT PRIMARY KEY, lat REAL, lon REAL, set_at TEXT)")
        conn.execute("INSERT OR REPLACE INTO anchor_state (session_id, lat, lon, set_at) VALUES (?, ?, ?, ?)", (session_id, lat, lon, now))
    return {"lat": lat, "lon": lon, "set_at": now}

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

@app.get("/api/sentry/anchor-drift")
def anchor_drift_check(session_id: str, lat: float, lon: float):
    anchor = get_anchor(session_id)
    if anchor is None:
        anchor = set_anchor(session_id, lat, lon)
        return {
            "status": "ANCHOR_SET",
            "message": "Anchor dropped at current position.",
            "anchor": [anchor["lat"], anchor["lon"]],
            "current": [lat, lon],
            "drift_m": 0.0,
        }

    drift_m = round(_haversine_m(anchor["lat"], anchor["lon"], lat, lon), 1)
    dragging = drift_m > ANCHOR_DRIFT_ALERT_M
    return {
        "status": "DRAGGING" if dragging else "HOLDING",
        "message": (
            f"Anchor dragging -- {drift_m}m from the dropped position."
            if dragging else
            f"Holding -- {drift_m}m from the dropped position."
        ),
        "anchor": [anchor["lat"], anchor["lon"]],
        "current": [lat, lon],
        "drift_m": drift_m,
        "alert_threshold_m": ANCHOR_DRIFT_ALERT_M,
    }

class AnchorResetRequest(BaseModel):
    session_id: str
    lat: float
    lon: float

@app.post("/api/sentry/anchor-drift/reset")
def anchor_drift_reset(request: AnchorResetRequest):
    anchor = set_anchor(request.session_id, request.lat, request.lon)
    return {"status": "ANCHOR_SET", "anchor": [anchor["lat"], anchor["lon"]], "set_at": anchor["set_at"]}

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
        "regional_zones": [],
        "language": "English",
        "persona": "Fisherman",
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

    session_store.append_turn(session_id, "user", request.user_message)
    session_store.append_turn(session_id, "assistant", final_advisory)
    session_store.set_last_context(session_id, coordinates, result.get("next_steps", []))

    return {
        "status": "success",
        "session_id": session_id,
        "user_message": request.user_message,
        "coordinates": coordinates,
        "advisory": final_advisory,
        "agents_invoked": result.get("next_steps", []),
        "query_intent": result.get("query_intent", ""),
        "language": result.get("language", "English"),
        "persona": result.get("persona", "Fisherman"),
        "hazard_status": _derive_hazard_status(boundary_report, ocean_report, hazard_report),
        "pfz_location": pfz_zones,
        "telemetry": _build_telemetry(
            lat, lon, ocean_report, chlorophyll_report,
            sst_delta=request.sst_delta, chlorophyll_delta=request.chlorophyll_delta,
            salinity_delta=request.salinity_delta,
        ),
        "lightning_alert": hazard_report["lightning_alert"],
        "cyclone_alert": hazard_report["cyclone_alert"],
        "hazard_summary": hazard_report["summary"],
        "route": route,
        "plot_url": result.get("plot_url"),
        "regional_zones": result.get("regional_zones", []),
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
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

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
        "regional_zones": [],
        "language": transcription["language"],
        "persona": "Fisherman",
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

    advisory_text = result.get("final_advisory", "Advisory generated successfully.")

    audio_url = None
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
    }

class DispatchRequest(BaseModel):
    coordinates: list[float]
    persona: str = "Fisherman"
    language: str = "English"
    day_offset: int = 0
    target_hour: int | None = 8

@app.post("/api/dispatch/generate")
def generate_dispatch(request: DispatchRequest):
    lat, lon = request.coordinates[0], request.coordinates[1]
    try:
        result = generate_morning_dispatch(
            lat, lon,
            persona=request.persona,
            language=request.language,
            day_offset=request.day_offset,
            target_hour=request.target_hour,
        )
    except Exception as e:
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    return {"status": "success", **result}