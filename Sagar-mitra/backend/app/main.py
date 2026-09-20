import os
import re
import traceback
import uuid
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv()  # reads .env in the working directory, if present

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.graph import create_orca_graph
from app.state import AgentState
from app.nlp_extract import extract_coordinates_from_message, extract_target_datetime_from_message
from app.statistical_engine import PFZStatisticalValidator
from app.pfz_ml import predict_pfz_confidence
from app.route_planner import plan_safe_route
from app.session_store import store as session_store
from app.data import store

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
# http://127.0.0.1:8000/static/plots/TEMP_trend_xxxx.png.
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Compile the LangGraph orchestrator on startup. create_orca_graph() itself
# enforces the strict Gemini-key startup check (see app/advisory.py's
# require_gemini_key) -- a missing/invalid key fails startup here with
# clear terminal instructions instead of starting a server that silently
# degrades every request.
orca_graph = create_orca_graph()

# --- Request Model ------------------------------------------------------
class OrchestrateRequest(BaseModel):
    user_message: str
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str | None = None  # carried across turns for conversation memory


# --- Dashboard signal derivation ------------------------------------------
# These checks are cheap and deterministic, so we run them for EVERY
# request regardless of which agent(s) the planner selected for the user's
# actual question. Otherwise the hazard banner, PFZ map, and route would
# only ever update when the planner happened to pick that domain, and would
# silently show a stale/default value the rest of the time.
_PFZ_COORD_RE = re.compile(r"Coordinates:\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]")
_PFZ_ZONE_HALF_WIDTH_DEG = 0.08  # ~9 km box drawn around the nearest known PFZ point


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


def _build_telemetry(lat: float, lon: float, ocean_report: str, chlorophyll_report: str) -> dict:
    """
    Builds the three Prediction Telemetry values from real, live-computed
    signals instead of the frontend's old hardcoded 85%/72%/91% placeholders:

      - sst_anomaly_pct: Z-Test confidence (1 - p_value) that live SST at
        this coordinate deviates from the Arabian Sea baseline.
      - chlorophyll_gradient_pct: same Z-Test confidence, for chlorophyll --
        i.e. how strong the biological-productivity gradient is here.
      - ml_confidence_pct: the trained PFZ classifier's own predicted
        probability for this point (None if the model hasn't been trained
        yet -- see backend/scripts/train_pfz_model.py).
    """
    sst_match = _SST_RE.search(ocean_report)
    chl_match = _CHLOROPHYLL_RE.search(chlorophyll_report)

    sst = float(sst_match.group(1)) if sst_match else None
    chlorophyll = float(chl_match.group(1)) if chl_match else None
    # No live salinity feed is wired up yet -- use the real historical
    # Arabian Sea baseline (computed from actual Argo data) as the best
    # available stand-in, rather than fabricating a "current" reading.
    salinity = store.calibrated_clim["sal"]["median"]

    sst_anomaly_pct = None
    if sst is not None:
        z_check = _pfz_validator.zscore_baseline_check("sst", sst)
        sst_anomaly_pct = round((1 - z_check["p_value"]) * 100, 1)

    chlorophyll_gradient_pct = None
    if chlorophyll is not None:
        chl_check = _pfz_validator.zscore_baseline_check("chlorophyll", chlorophyll)
        chlorophyll_gradient_pct = round((1 - chl_check["p_value"]) * 100, 1)

    ml_confidence_pct = None
    if sst is not None and chlorophyll is not None:
        ml_confidence_pct = predict_pfz_confidence(sst, chlorophyll, salinity, lat, lon)

    return {
        "sst_anomaly_pct": sst_anomaly_pct,
        "chlorophyll_gradient_pct": chlorophyll_gradient_pct,
        "ml_confidence_pct": ml_confidence_pct,
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
        raise HTTPException(status_code=500, detail=f"Internal error during orchestration: {e}")

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
        "telemetry": _build_telemetry(lat, lon, ocean_report, chlorophyll_report),
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
