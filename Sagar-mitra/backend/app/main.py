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

# --- CORS ---------------------------------------------------------------
# Wide open for the hackathon so the frontend can connect freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves the historical-chart PNGs app/historical.py saves under
# backend/static/plots -- the plot_url returned to the frontend (see
# run_orchestration below) points at this mount, e.g.
# http://127.0.0.1:8000/static/plots/TEMP_trend_xxxx.png. Also serves
# synthesized advisory audio saved under backend/static/audio (see
# app/voice.py's save_advisory_audio).
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
    user_message: str
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str | None = None  # carried across turns for conversation memory
    # SHAP "What-If" sensitivity slider: optional perturbations applied to the
    # ML confidence inputs before predict_pfz_confidence runs, so the
    # frontend can ask "what if SST/chlorophyll/salinity were different here"
    # without a second round-trip. Bounded to plausible physical swings so a
    # bad slider value can't be passed straight into the model.
    sst_delta: float | None = Field(default=None, ge=-10, le=10)
    chlorophyll_delta: float | None = Field(default=None, ge=-5, le=5)
    salinity_delta: float | None = Field(default=None, ge=-10, le=10)


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
    three-tier vocabulary _derive_hazard_status already uses for the main
    hazard banner, so the frontend can reuse its existing hazard-banner CSS
    classes for this too instead of inventing a fourth status vocabulary.
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


# --- Prediction Telemetry (real values, not the old hardcoded 85/72/91) ---
_SST_RE = re.compile(r"Water Temp:\s*([-\d.]+)")
_CHLOROPHYLL_RE = re.compile(r"Chlorophyll-a:\s*([\d.]+)")
_pfz_validator = PFZStatisticalValidator()


def _build_telemetry(
    lat: float, lon: float, ocean_report: str, chlorophyll_report: str,
    sst_delta: Optional[float] = None, chlorophyll_delta: Optional[float] = None,
    salinity_delta: Optional[float] = None,
) -> dict:
    """
    Builds the Prediction Telemetry values from real, live-computed signals
    instead of the frontend's old hardcoded 85%/72%/91% placeholders:

      - sst_anomaly_pct: Z-Test confidence (1 - p_value) that live SST at
        this coordinate deviates from the Arabian Sea baseline.
      - chlorophyll_gradient_pct: same Z-Test confidence, for chlorophyll --
        i.e. how strong the biological-productivity gradient is here.
      - salinity_anomaly_pct: same Z-Test confidence for salinity. No live
        salinity feed is wired up yet, so this checks the dataset's own
        calibrated median (store.calibrated_clim) against the
        PFZStatisticalValidator's independent Arabian Sea baseline rather
        than fabricating a "current" reading.
      - ph_gradient_pct: None -- no live OR dataset-observed pH feed exists
        anywhere in this app (see app/data.py's calibrated_clim comment:
        "not in this dataset; kept as fallback"). Returned as None rather
        than a fabricated synthetic signal, matching how sst/chlorophyll
        are already None when their own regex match fails below.
      - ml_confidence_pct: the trained PFZ classifier's own predicted
        probability for this point (None if the model hasn't been trained
        yet -- see backend/scripts/train_pfz_model.py).
      - shap_attributions: per-feature SHAP attributions explaining
        ml_confidence_pct (Feature/Task: SHAP explainability -- see
        pfz_ml.py's include_shap flag), None if unavailable. Only the
        Researcher persona's advisory card renders this (see index.html's
        appendAdvisoryCard) -- it's still computed for every request here
        since the SST/chlorophyll/salinity signals it needs are already
        being fetched for the other two telemetry values anyway.

    The four independent checks below (sst/chlorophyll/salinity z-tests +
    the ML/SHAP call) don't depend on each other's results, so they run
    concurrently via a thread pool instead of one after another -- the
    ML/SHAP call in particular does real model-inference work, so this is
    genuine parallelism, not just bookkeeping.
    """
    sst_match = _SST_RE.search(ocean_report)
    chl_match = _CHLOROPHYLL_RE.search(chlorophyll_report)

    sst = float(sst_match.group(1)) if sst_match else None
    chlorophyll = float(chl_match.group(1)) if chl_match else None
    # No live salinity feed is wired up yet -- use the real historical
    # Arabian Sea baseline (computed from actual Argo data) as the best
    # available stand-in, rather than fabricating a "current" reading.
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
        return None  # no live/observed pH signal exists to check -- see docstring above

    def _ml_confidence():
        if sst is None or chlorophyll is None:
            return None, None
        # What-If sliders perturb only the ML/SHAP inputs, not the z-test
        # anomaly signals above -- those describe real observed conditions,
        # while this branch answers "what would the model say if...".
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
    """
    Feature 3 (Proactive IMBL/Geofence Siren): a lightweight, poll-friendly
    endpoint the frontend calls on an interval (not on every chat query --
    see /api/orchestrate for that), so a vessel drifting toward the EEZ
    boundary or a Marine Protected Area gets a warning before it next asks
    ORCA anything. See boundary_toool.distance_to_nearest_boundary_km for
    the underlying proximity math and check_maritime_boundary for the
    confirmed-breach text used elsewhere in the advisory pipeline.
    """
    boundary = distance_to_nearest_boundary_km(lat, lon)
    alert_level, message = _derive_geofence_alert(boundary)
    # Feature 3 polish -- only computed (and non-None) once the vessel has
    # actually left safe water; a SAFE verdict has no return heading to give.
    return_heading = return_heading_to_safety(lat, lon) if alert_level != "SAFE" else None
    return {
        "coordinates": [lat, lon],
        **boundary,
        "geofence_alert": alert_level,
        "message": message,
        "return_heading": return_heading,
    }


# --- Feature: Sentry / Anchor Drift Alarm ---------------------------------
import math
import sqlite3
import datetime

ANCHOR_DRIFT_ALERT_M = 50.0  # metres of drift before this is flagged as dragging

def get_anchor(session_id: str):
    with sqlite3.connect("data/sagar_mitra_store.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS anchor_state (session_id TEXT PRIMARY KEY, lat REAL, lon REAL, set_at TEXT)")
        row = conn.execute("SELECT lat, lon FROM anchor_state WHERE session_id = ?", (session_id,)).fetchone()
        return {"lat": row[0], "lon": row[1]} if row else None

def set_anchor(session_id: str, lat: float, lon: float):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
    """
    Lightweight anchor-drag check. The first call for a given session_id
    drops the anchor at the supplied position (nothing to compare drift
    against yet); every call after that compares the current position
    against the stored anchor and flags dragging past
    ANCHOR_DRIFT_ALERT_M metres. State persists in db_store.py's
    anchor_state table (data/sagar_mitra_store.db) so a server restart
    doesn't lose the anchor mid-watch.
    """
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
    """Re-drops the anchor at the given position, replacing any previous
    reference point for this session (e.g. after deliberately repositioning)."""
    anchor = set_anchor(request.session_id, request.lat, request.lon)
    return {"status": "ANCHOR_SET", "anchor": [anchor["lat"], anchor["lon"]], "set_at": anchor["set_at"]}


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
    """
    Logs a mayday/SOS event to the persistent store (app/db.py's sos_events
    table -- see Task 1) instead of only ever showing a local alert() in the
    browser (see index.html's triggerMayday). Every field here mirrors what
    triggerMayday's payload sends: the vessel's last known coordinates, the
    last known hazard status, and the (currently hardcoded) nearest-port
    text shown in its mayday message.
    """
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
    """
    Feature 13: SIMULATED maritime boundary violation escalation. Logs a
    telemetry event to the local ops queue (db.insert_escalation_event) so
    a confirmed EEZ/MPA breach has an auditable trail. This does NOT
    dispatch to a real Coast Guard system -- no such integration exists
    (see ROADMAP.md's Non-Goals) -- and the response says so plainly rather
    than implying a live dispatch happened.
    """
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
    hazard_type: str  # e.g. "net", "oil_slick", "debris"
    status: str | None = None


@app.post("/api/hazard")
def report_hazard(request: HazardReportRequest):
    """
    Feature 7 (Crowdsourced Hazard Mesh Network): logs a geocoded hazard
    report to app/db_store.py's hazard_mesh table (previously a dead
    schema -- insert_hazard_point/get_hazard_mesh existed but nothing
    called them). See GET /api/hazard/mesh for the 24h-TTL read side.
    """
    point_id = insert_hazard_point(request.lat, request.lon, request.hazard_type, request.status)
    return {"status": "success", "id": point_id}


@app.get("/api/hazard/mesh")
def get_hazard_mesh_endpoint(ttl_hours: float = 24.0, limit: int = 1000):
    """Reports from the last `ttl_hours` only (default 24h) -- see
    db_store.get_hazard_mesh's TTL filter."""
    return {"points": get_hazard_mesh(limit=limit, ttl_hours=ttl_hours)}


@app.get("/api/news")
def get_news(domain: str | None = None):
    """
    Task 3: top 5 ScienceDaily Oceanography RSS headlines, 1-hour cached
    (see app/news_feed.py). Optional `?domain=` filters to articles tagged
    with that domain slug (see app/news_feed.py's DOMAIN_TAXONOMY); an
    unrecognized/omitted domain returns the full unfiltered set.
    """
    return {"articles": get_oceanography_news(limit=5, domain=domain)}


@app.get("/api/news/domains")
def get_news_domains():
    """Ocean domain taxonomy slugs, for the frontend's news domain selector
    (see app/news_feed.py's DOMAIN_TAXONOMY)."""
    return {"domains": list(DOMAIN_TAXONOMY.keys())}


@app.post("/api/orchestrate")
def run_orchestration(request: OrchestrateRequest):
    # Conversation memory: a session_id lets a follow-up ("and what about
    # tomorrow?") be answered with the last few turns as context. The
    # frontend persists this in localStorage; if none is supplied (first
    # visit, or a direct API caller), a fresh one is minted and returned so
    # the caller can carry it forward.
    session_id = request.session_id or str(uuid.uuid4())
    history = session_store.get_history(session_id)
    last_context = session_store.get_last_context(session_id)
    last_agents = last_context["agents"] if last_context else []

    # Coordinate resolution: a place named IN THE MESSAGE ("fishing zones
    # near Chennai") always takes priority over the vessel's own reported
    # GPS position. When the message names no place of its own -- e.g. a
    # referential follow-up like "and what about tomorrow morning instead?"
    # -- fall back to the SAME location this session was just discussing
    # (not the vessel's raw GPS default), so follow-ups stay on-topic. Only
    # a brand-new session with no prior turn falls back to the vessel's GPS.
    extracted = extract_coordinates_from_message(request.user_message)
    if extracted:
        coordinates = list(extracted)
    elif last_context:
        coordinates = last_context["coordinates"]
    else:
        coordinates = request.coordinates

    # "Is it safe tomorrow morning?" -- regex-only, no LLM call, so it never
    # adds latency/quota cost and still works with no Gemini key configured.
    # (0, None) means no future date/time was mentioned, in which case every
    # downstream tool call below behaves exactly as it did before this was
    # added (fetches "current" conditions).
    day_offset, target_hour = extract_target_datetime_from_message(request.user_message)

    # Package incoming request into the AgentState format
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
        # Run the compiled graph workflow (planner -> dispatch -> synthesizer)
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    lat, lon = coordinates[0], coordinates[1]
    # The graph's dispatch_node already fetched boundary/ocean/PFZ/
    # chlorophyll/hazard data ONCE, concurrently, for this exact coordinate
    # (see graph.py's _fetch_common_signals) -- reuse that result instead of
    # making the same five live calls again here. This used to be the #1
    # source of the ~23s-per-query latency: every request paid for these
    # signals TWICE, once inside whichever chat agents the planner picked,
    # and once more here unconditionally.
    common = result.get("common_signals") or {}
    boundary_report = common.get("boundary_report", "")
    # PFZ/chlorophyll have no free forecast product to fall back to (INCOIS's
    # PFZ advisory and NOAA's chlorophyll composite are both "today only"),
    # so those two stay as-is -- only wave/weather conditions and hazard
    # alerts can honestly answer a future-dated question.
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

    # Persist this turn so the next request on the same session_id has
    # context for follow-up questions -- both the dialogue text AND the
    # resolved location/topic, so a referential follow-up with no place
    # name or domain keyword of its own still knows what "those conditions"
    # and "there" refer to.
    session_store.append_turn(session_id, "user", request.user_message)
    session_store.append_turn(session_id, "assistant", final_advisory)
    session_store.set_last_context(session_id, coordinates, result.get("next_steps", []))

    # Return the final synthesized response as JSON to the frontend
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
        # Structured fields for the frontend to render directly (see
        # index.html's appendAdvisoryCard/plotRegionalZones) instead of only
        # ever being embedded as prose inside `advisory`, where a Gemini
        # synthesis pass could paraphrase away a raw URL or drop the zone
        # list entirely.
        "plot_url": result.get("plot_url"),
        "regional_zones": result.get("regional_zones", []),
        # Tells the frontend/user which date+time the wave/weather/hazard
        # fields above actually describe -- None means "current conditions"
        # (no future date/time was mentioned in the query).
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
):
    """
    Accepts a spoken query (Marathi, Tamil, Telugu, Gujarati, Malayalam, or
    English), transcribes + translates it via Gemini, runs the English
    translation through the same LangGraph workflow as /api/orchestrate
    (producing the final advisory natively in the detected language), and
    synthesizes that advisory back into speech.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="No audio data received.")
    mime_type = audio.content_type or "audio/wav"

    try:
        transcription = transcribe_and_translate(audio_bytes, mime_type)
    except UnsupportedAudioError as e:
        # Don't guess at what was said - tell the user plainly instead.
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
            # Don't let the raw Gemini error JSON (which can include the full
            # error body) reach the agent stream - show a plain status instead.
            raise HTTPException(
                status_code=403,
                detail="The voice transcription service isn't authorized to process "
                       "this request right now. Please try again later or contact support.",
            )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    initial_state: AgentState = {
        # The native-script transcript, not the English translation -- the
        # planner detects language/persona/intent directly from this message
        # (it handles any language, see app/planner.py) and that detection
        # decides what language the final advisory/TTS come back in. Feeding
        # it the English translation would always detect "English" here.
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
        # Voice output is on top of the text advisory - if TTS fails, still
        # return the text result rather than failing the whole request.
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


# --- Feature 4: Offline "Morning Dispatch" --------------------------------
class DispatchRequest(BaseModel):
    coordinates: list[float]  # e.g., [18.9, 72.8]
    persona: str = "Fisherman"
    language: str = "English"
    day_offset: int = 0        # 0 = today, 1 = tomorrow, ...
    target_hour: int | None = 8  # hour-of-day (24h) the briefing's conditions should describe


@app.post("/api/dispatch/generate")
def generate_dispatch(request: DispatchRequest):
    """
    Generates a downloadable pre-departure briefing (PDF + spoken audio) of
    today's tides/waves, nearest PFZ, hazard alerts, boundary status, and
    top favorable regions -- meant to be called ONCE while still online in
    port, then read/played back later with no connectivity at sea. See
    app/dispatch.py for the generation pipeline.
    """
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
