"""
Sagar Mitra / ORCA - Conversation Session Store
===================================================
Gives /api/orchestrate multi-turn memory: each request carries a
`session_id`, and this store keeps:

  1. The last few turns of dialogue (for the synthesizer's context and for
     the planner to resolve referential questions like "those same
     conditions").
  2. The last RESOLVED coordinates and agent selection for that session, so
     a follow-up with no place name of its own ("and what about tomorrow
     morning?") continues talking about the same location and topic instead
     of silently falling back to the vessel's raw GPS position and a
     keyword-default agent guess.

Hackathon-scope only: sessions live in this single process's memory and are
lost on restart, and won't be shared across multiple backend instances.
Good enough for a single-instance FastAPI deployment -- swap the storage
here for Redis/a DB if this ever needs to survive restarts or scale out.
"""
from collections import defaultdict
from typing import Dict, List, Optional

MAX_TURNS_KEPT = 8  # last 8 (user+assistant) messages is plenty of context


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, List[dict]] = defaultdict(list)
        self._last_context: Dict[str, dict] = {}

    def get_history(self, session_id: str) -> List[dict]:
        return list(self._sessions.get(session_id, []))

    def append_turn(self, session_id: str, role: str, text: str) -> None:
        if not text:
            return
        turns = self._sessions[session_id]
        turns.append({"role": role, "text": text})
        del turns[:-MAX_TURNS_KEPT]

    def replace_history(self, session_id: str, history: List[dict], clear_context: bool = False) -> None:
        """Resync a conversation from its client transcript (used by edits/reload)."""
        self._sessions[session_id] = [
            {"role": item["role"], "text": item["text"]}
            for item in history[-MAX_TURNS_KEPT:]
            if item.get("role") in {"user", "assistant"} and item.get("text")
        ]
        if clear_context:
            self._last_context.pop(session_id, None)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._last_context.pop(session_id, None)

    def get_last_context(self, session_id: str) -> Optional[dict]:
        """Returns {"coordinates": [lat, lon], "agents": [...]} from the
        previous turn on this session, or None for a brand-new session."""
        return self._last_context.get(session_id)

    def set_last_context(self, session_id: str, coordinates: List[float], agents: List[str]) -> None:
        self._last_context[session_id] = {"coordinates": coordinates, "agents": agents}


store = SessionStore()
