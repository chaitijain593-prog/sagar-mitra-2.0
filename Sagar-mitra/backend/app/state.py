from typing import TypedDict, List, Dict, Optional


class AgentState(TypedDict):
    user_message: str
    coordinates: List[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str
    day_offset: int  # 0 = today, 1 = tomorrow, 2 = day after tomorrow
    target_hour: Optional[int]  # hour-of-day (24h) mentioned, e.g. 8 for "morning"
    history: List[dict]  # [{"role": "user"|"assistant", "text": str}, ...], oldest first
    last_agents: List[str]  # agents selected on the PREVIOUS turn of this session (fallback hint)
    next_steps: List[str]  # agents selected by the planner, e.g. ["navigation", "fishing"]
    agent_reports: Dict[str, str]  # agent name -> that agent's raw finding
    hazard_alerts: List[str]
    # Boundary/ocean/PFZ/chlorophyll/hazard signals fetched ONCE per request
    # (concurrently, in dispatch_node) and reused by both the matching chat
    # agents (navigation/fishing/compliance/hazard) AND main.py's dashboard
    # telemetry/route/PFZ-map derivation -- see graph.py's
    # _fetch_common_signals. Keys: boundary_report, ocean_report, pfz_report,
    # chlorophyll_report, hazard_report.
    common_signals: Dict[str, object]
    plot_url: Optional[str]  # historical chart image URL, if the historical agent generated one
    regional_zones: List[dict]  # ranked zones from the regional agent, for map markers
    dispatch_pdf_url: Optional[str]  # Morning Dispatch PDF, if the dispatch agent ran (see sub_agents.py)
    dispatch_audio_url: Optional[str]  # Morning Dispatch spoken audio, if TTS succeeded
    language: str
    persona: str
    # Vessel/operator category declared at onboarding (e.g. "artisanal_coastal",
    # "mechanized_trawler") -- see main.py's reconcile_persona_key and
    # advisory.py's VESSEL_PERSONA_SYSTEM_PROMPTS. Distinct from `persona`
    # above, which is the AUDIENCE communication style (Fisherman/Student/
    # Researcher/General Public) the planner detects live from message tone.
    vessel_persona: str
    query_intent: str
    final_output: str
    final_advisory: str
