import os
import traceback
from dotenv import load_dotenv
load_dotenv()  # reads .env in the working directory, if present

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.graph import create_orca_graph
from app.state import AgentState
from app.voice import transcribe_and_translate, synthesize_speech, save_advisory_audio, UnsupportedAudioError
from app.advisory import _is_quota_error, _is_permission_denied_error
from app.route_tool import compute_safe_route


def _orchestration_error_detail(e: Exception) -> str:
    if _is_quota_error(e):
        return ("The AI service has hit its API quota/rate limit right now. "
                "Please wait a bit and try again.")
    return f"Internal error during orchestration: {e}"

app = FastAPI(title="ORCA Backend API", version="0.1.0")

# --- CORS ---------------------------------------------------------------
# Wide open for the hackathon so the frontend can connect freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (generated plots + advisory audio) ---------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Compile the LangGraph orchestrator on startup
orca_graph = create_orca_graph()

# --- Request Model ------------------------------------------------------
class OrchestrateRequest(BaseModel):
    user_message: str
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai


class SafeRouteRequest(BaseModel):
    start: list[float]  # [lat, lon] vessel position
    end: list[float]    # [lat, lon] destination (e.g. a PFZ)


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
    # Package incoming request into the AgentState format
    initial_state: AgentState = {
        "user_message": request.user_message,
        "coordinates": request.coordinates,
        "next_step": "",
        "hazard_alerts": [],
        "final_output": "",
        "final_advisory": "",
        "language": "English",
    }

    try:
        # Run the compiled graph workflow
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        status_code = 429 if _is_quota_error(e) else 500
        raise HTTPException(status_code=status_code, detail=_orchestration_error_detail(e))

    # Return the final synthesized response as JSON to the frontend
    return {
        "status": "success",
        "user_message": request.user_message,
        "coordinates": request.coordinates,
        "advisory": result.get("final_advisory", "Advisory generated successfully.")
    }


# --- Feature 2: Weather-Aware Safe Route Optimization --------------------
@app.post("/api/route/safe")
def safe_route(request: SafeRouteRequest):
    """
    Computes an A*-based safe trajectory from `start` to `end`, treating
    rough seas (wave height > 2.5m), severe weather zones, and restricted
    EEZ/MPA boundaries as impassable obstacles. Returns the path plus
    estimated trip duration and fuel-use metrics.
    """
    if len(request.start) != 2 or len(request.end) != 2:
        raise HTTPException(status_code=422, detail="start and end must each be [lat, lon].")

    try:
        result = compute_safe_route(tuple(request.start), tuple(request.end))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Route computation failed: {e}")

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message", "No safe route found."))

    return result


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
        "user_message": transcription["english_text"],
        "coordinates": [latitude, longitude],
        "next_step": "",
        "hazard_alerts": [],
        "final_output": "",
        "final_advisory": "",
        "language": transcription["language"],
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