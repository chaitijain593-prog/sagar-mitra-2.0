"""
Sagar Mitra / ORCA - Small TTL Cache for LLM Calls
======================================================
The free-tier Gemini quota is 20 requests/day, and a single /api/orchestrate
call can burn 2-4 of those (planner + per-agent + synthesizer). Repeated or
near-identical questions -- common both in demos and in judges retesting the
same query -- shouldn't each cost a fresh call. This is a plain in-memory
cache, not a correctness mechanism: it only short-circuits calls whose
result is safe to reuse for a few minutes (query planning, historical/
archival lookups), never live sensor readings.
"""
import time
from typing import Any, Callable, Optional


class TTLCache:
    def __init__(self, ttl_seconds: float = 600):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time() + self.ttl, value)

    def get_or_set(self, key: str, compute: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value)
        return value


def normalize_key(*parts: str) -> str:
    return "|".join(p.strip().lower() for p in parts if p)
