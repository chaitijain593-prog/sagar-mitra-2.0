"""
Sagar Mitra / ORCA - Anchor Drift Sentry Store
===================================================
Feature 10: lets a vessel drop a virtual anchor (a lat/lon plus a safe drift
radius) for its session, so /api/sentry/anchor-drift can later tell the
frontend how far the vessel has drifted from that point.

Hackathon-scope only: anchors live in this single process's memory and are
lost on restart -- same tradeoff session_store.py takes for conversation
memory. Swap for Redis/a DB if this ever needs to survive restarts or scale
out across multiple backend instances.
"""
from typing import Dict, Optional


class AnchorStore:
    def __init__(self):
        self._anchors: Dict[str, dict] = {}

    def set_anchor(self, session_id: str, lat: float, lon: float, radius_km: float) -> None:
        self._anchors[session_id] = {"lat": lat, "lon": lon, "radius_km": radius_km}

    def get_anchor(self, session_id: str) -> Optional[dict]:
        return self._anchors.get(session_id)

    def clear_anchor(self, session_id: str) -> None:
        self._anchors.pop(session_id, None)


store = AnchorStore()
