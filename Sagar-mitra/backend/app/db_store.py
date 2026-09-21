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
from typing import Dict, List, Optional

DB_PATH = os.environ.get("SAGAR_MITRA_STORE_DB_PATH", "./data/sagar_mitra_store.db")
MAX_TURNS_KEPT = 8  # last 8 (user+assistant) messages is plenty of context


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
            status TEXT
        )
    """)
    conn.commit()


class SessionStore:
    """SQLite-backed drop-in replacement for session_store.SessionStore."""

    def __init__(self):
        self._conn = _get_connection()
        _init_schema(self._conn)

    def _load_row(self, session_id: str) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT history, last_context FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        return cur.fetchone()

    def get_history(self, session_id: str) -> List[dict]:
        row = self._load_row(session_id)
        if row is None:
            return []
        return json.loads(row["history"])

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

    def get_last_context(self, session_id: str) -> Optional[dict]:
        """Returns {"coordinates": [lat, lon], "agents": [...]} from the
        previous turn on this session, or None for a brand-new session."""
        row = self._load_row(session_id)
        if row is None or row["last_context"] is None:
            return None
        return json.loads(row["last_context"])

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
    conn = _get_connection()
    try:
        _init_schema(conn)
        cur = conn.execute(
            "INSERT INTO hazard_mesh (lat, lon, type, status) VALUES (?, ?, ?, ?)",
            (lat, lon, hazard_type, status),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_hazard_mesh(limit: int = 1000) -> List[dict]:
    conn = _get_connection()
    try:
        _init_schema(conn)
        cur = conn.execute(
            "SELECT * FROM hazard_mesh ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


store = SessionStore()
