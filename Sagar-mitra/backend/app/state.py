from typing import TypedDict, List


class AgentState(TypedDict):
    user_message: str
    coordinates: List[float]  # e.g., [18.9, 72.8] for Mumbai
    next_step: str
    hazard_alerts: List[str]
    final_output: str
    final_advisory: str
