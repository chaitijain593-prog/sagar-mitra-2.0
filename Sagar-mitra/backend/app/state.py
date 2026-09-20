from typing import TypedDict, List, Dict


class AgentState(TypedDict):
    user_message: str
    coordinates: List[float]  # e.g., [18.9, 72.8] for Mumbai
    session_id: str
    history: List[dict]  # [{"role": "user"|"assistant", "text": str}, ...], oldest first
    last_agents: List[str]  # agents selected on the PREVIOUS turn of this session (fallback hint)
    next_steps: List[str]  # agents selected by the planner, e.g. ["navigation", "fishing"]
    agent_reports: Dict[str, str]  # agent name -> that agent's raw finding
    hazard_alerts: List[str]
    language: str
    persona: str
    query_intent: str
    final_output: str
    final_advisory: str
