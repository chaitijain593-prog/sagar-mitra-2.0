import os
import traceback
from dotenv import load_dotenv
load_dotenv()  # reads .env in the working directory, if present

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.graph import create_orca_graph
from app.state import AgentState

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

# Compile the LangGraph orchestrator on startup
orca_graph = create_orca_graph()

# --- Request Model ------------------------------------------------------
class OrchestrateRequest(BaseModel):
    user_message: str
    coordinates: list[float]  # e.g., [18.9, 72.8] for Mumbai


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
        "final_advisory": ""
    }
    
    try:
        # Run the compiled graph workflow
        result = orca_graph.invoke(initial_state)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error during orchestration: {e}")
    
    # Return the final synthesized response as JSON to the frontend
    return {
        "status": "success",
        "user_message": request.user_message,
        "coordinates": request.coordinates,
        "advisory": result.get("final_advisory", "Advisory generated successfully.")
    }