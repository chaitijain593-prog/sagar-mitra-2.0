"""
Sagar Mitra / ORCA - SQLite-backed session/hazard store
===========================================================
Replaces app/session_store.py's pure in-memory dicts with SQLite so
conversation history and the hazard mesh survive a process restart.
Exposes the SAME `store` object API as session_store.py (get_history,
append_turn, get_last_context, set_last_context), so main.py's
`from app.session_store import store as session_store` line becomes
`from app.db_store import store as session_store` and nothing else in
main.py changes.

SOS logging is NOT duplicated here -- app/db.py already owns the
`sos_events` table (POST /api/sos writes there), so this module only
covers sessions and the hazard mesh.
"""
import json
import os
import sqlite3
import threading
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

DB_PATH = os.environ.get("SAGAR_MITRA_STORE_DB_PATH", "./data/sagar_mitra_store.db")
MAX_TURNS_KEPT = 8  # last 8 (user+assistant) messages is plenty of context
HAZARD_MESH_TTL_HOURS = 24.0  # Feature 7: crowdsourced hazard reports expire after this many hours


def _serialized(method):
    """Serialize access to this worker's shared SQLite connection."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapped


def _get_connection() -> sqlite3.Connection:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            history TEXT NOT NULL,
            last_context TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hazard_mesh (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            type TEXT NOT NULL,
            status TEXT,
            timestamp TEXT
        )
    """)
    # Migration: a hazard_mesh table created before the TTL column existed
    # (this table was dead code with zero writes, but guard anyway rather
    # than assume) won't have `timestamp` -- add it instead of dropping the
    # table, so this stays safe to run on every startup.
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(hazard_mesh)")}
    if "timestamp" not in existing_cols:
        conn.execute("ALTER TABLE hazard_mesh ADD COLUMN timestamp TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anchor_state (
            session_id TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            set_at TEXT NOT NULL,
            radius_km REAL NOT NULL DEFAULT 0.5
        )
    """)
    anchor_cols = {row[1] for row in conn.execute("PRAGMA table_info(anchor_state)")}
    if "radius_km" not in anchor_cols:
        conn.execute("ALTER TABLE anchor_state ADD COLUMN radius_km REAL NOT NULL DEFAULT 0.5")
    conn.commit()


class SessionStore:
    """SQLite-backed drop-in replacement for session_store.SessionStore."""

    def __init__(self):
        self._lock = threading.RLock()
        self._conn = _get_connection()
        _init_schema(self._conn)

    def _load_row(self, session_id: str) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT history, last_context FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        return cur.fetchone()

    @_serialized
    def get_history(self, session_id: str) -> List[dict]:
        row = self._load_row(session_id)
        if row is None:
            return []
        return json.loads(row["history"])

    @_serialized
    def append_turn(self, session_id: str, role: str, text: str) -> None:
        if not text:
            return
        row = self._load_row(session_id)
        turns = json.loads(row["history"]) if row else []
        turns.append({"role": role, "text": text})
        del turns[:-MAX_TURNS_KEPT]
        last_context = row["last_context"] if row else None
        self._conn.execute(
            """
            INSERT INTO sessions (session_id, history, last_context)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET history = excluded.history
            """,
            (session_id, json.dumps(turns), last_context),
        )
        self._conn.commit()

    @_serialized
    def replace_history(self, session_id: str, history: List[dict], clear_context: bool = False) -> None:
        """Resync one conversation from its client transcript (edit/reload)."""
        row = self._load_row(session_id)
        turns = [
            {"role": item["role"], "text": item["text"]}
            for item in history[-MAX_TURNS_KEPT:]
            if item.get("role") in {"user", "assistant"} and item.get("text")
        ]
        last_context = None if clear_context or row is None else row["last_context"]
        self._conn.execute(
            """
            INSERT INTO sessions (session_id, history, last_context)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                history = excluded.history,
                last_context = excluded.last_context
            """,
            (session_id, json.dumps(turns), last_context),
        )
        self._conn.commit()

    @_serialized
    def delete_session(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self._conn.commit()

    @_serialized
    def get_last_context(self, session_id: str) -> Optional[dict]:
        """Returns {"coordinates": [lat, lon], "agents": [...]} from the
        previous turn on this session, or None for a brand-new session."""
        row = self._load_row(session_id)
        if row is None or row["last_context"] is None:
            return None
        return json.loads(row["last_context"])

    @_serialized
    def set_last_context(self, session_id: str, coordinates: List[float], agents: List[str]) -> None:
        row = self._load_row(session_id)
        history = row["history"] if row else json.dumps([])
        last_context = json.dumps({"coordinates": coordinates, "agents": agents})
        self._conn.execute(
            """
            INSERT INTO sessions (session_id, history, last_context)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET last_context = excluded.last_context
            """,
            (session_id, history, last_context),
        )
        self._conn.commit()


# --- Hazard mesh -------------------------------------------------------------

def insert_hazard_point(lat: float, lon: float, hazard_type: str,
                         status: Optional[str] = None) -> int:
    """Feature 7 (Crowdsourced Hazard Mesh Network): logs a geocoded hazard
    report (net, slick, debris, etc.). Timestamped in UTC so
    get_hazard_mesh's TTL filter below can expire it consistently
    regardless of the server's local timezone."""
    conn = _get_connection()
    try:
        _init_schema(conn)
        timestamp = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO hazard_mesh (lat, lon, type, status, timestamp) VALUES (?, ?, ?, ?, ?)",
            (lat, lon, hazard_type, status, timestamp),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_hazard_mesh(limit: int = 1000, ttl_hours: float = HAZARD_MESH_TTL_HOURS) -> List[dict]:
    """Crowdsourced hazard reports from the last `ttl_hours` hours only -- a
    report older than the TTL is excluded (not deleted: a stale report is
    simply no longer surfaced, so the underlying history isn't destroyed by
    a read). A row written before this TTL column existed has `timestamp =
    NULL` and is excluded by the `>=` comparison below rather than raising,
    which is the right call for genuinely-unknown-age data."""
    conn = _get_connection()
    try:
        _init_schema(conn)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).isoformat()
        cur = conn.execute(
            "SELECT * FROM hazard_mesh WHERE timestamp >= ? ORDER BY id DESC LIMIT ?",
            (cutoff, limit),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# --- Anchor drift (Sentry) --------------------------------------------------

def get_anchor(session_id: str) -> Optional[dict]:
    """The dropped-anchor reference point for this session, or None if no
    anchor has been set yet."""
    conn = _get_connection()
    try:
        _init_schema(conn)
        row = conn.execute(
            "SELECT lat, lon, set_at, radius_km FROM anchor_state WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_anchor(session_id: str, lat: float, lon: float, radius_km: float = 0.5) -> dict:
    """Drops (or re-drops) the anchor reference point for this session at
    the given position, replacing any previous one."""
    conn = _get_connection()
    try:
        _init_schema(conn)
        set_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO anchor_state (session_id, lat, lon, set_at, radius_km)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                lat = excluded.lat, lon = excluded.lon, set_at = excluded.set_at,
                radius_km = excluded.radius_km
            """,
            (session_id, lat, lon, set_at, radius_km),
        )
        conn.commit()
        return {"lat": lat, "lon": lon, "set_at": set_at, "radius_km": radius_km}
    finally:
        conn.close()


def clear_anchor(session_id: str) -> None:
    conn = _get_connection()
    try:
        _init_schema(conn)
        conn.execute("DELETE FROM anchor_state WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


store = SessionStore()
