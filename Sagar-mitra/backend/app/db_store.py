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

    # Multi-device session persistence columns
    sess_cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "title" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
    if "workspace_id" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN workspace_id TEXT DEFAULT 'arabian'")
    if "full_transcript" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN full_transcript TEXT")
    if "created_at" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN created_at TEXT")
    if "updated_at" not in sess_cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN updated_at TEXT")

    # Scheduled Tasks & Background Events
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            task_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            workspace_id TEXT DEFAULT 'arabian',
            persona TEXT DEFAULT 'others',
            prompt TEXT NOT NULL,
            schedule_type TEXT NOT NULL,
            run_at TEXT NOT NULL,
            interval_seconds INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            coordinates TEXT NOT NULL,
            last_run TEXT,
            result_summary TEXT,
            result_payload TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_task_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            summary TEXT,
            completed_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            workspace_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
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
        self._conn.execute("DELETE FROM scheduled_tasks WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM scheduled_task_events WHERE session_id = ?", (session_id,))
        self._conn.commit()

    @_serialized
    def list_workspaces(self) -> List[dict]:
        cur = self._conn.execute(
            "SELECT workspace_id, name, created_at FROM workspaces ORDER BY rowid ASC"
        )
        return [
            {"workspace_id": r["workspace_id"], "name": r["name"], "created_at": r["created_at"]}
            for r in cur.fetchall()
        ]

    @_serialized
    def create_workspace(self, name: str, workspace_id: Optional[str] = None) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        ws_id = workspace_id or f"ws_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        self._conn.execute(
            "INSERT OR REPLACE INTO workspaces (workspace_id, name, created_at) VALUES (?, ?, ?)",
            (ws_id, name, now_iso)
        )
        self._conn.commit()
        return {"workspace_id": ws_id, "name": name, "created_at": now_iso}

    @_serialized
    def delete_workspace(self, workspace_id: str) -> None:
        self._conn.execute("DELETE FROM workspaces WHERE workspace_id = ?", (workspace_id,))
        self._conn.commit()

    @_serialized
    def list_sessions(self, limit: int = 50, workspace_id: Optional[str] = None) -> List[dict]:
        if workspace_id:
            cur = self._conn.execute(
                """
                SELECT session_id, title, workspace_id, created_at, updated_at, full_transcript
                FROM sessions
                WHERE workspace_id = ?
                ORDER BY COALESCE(updated_at, created_at, rowid) DESC
                LIMIT ?
                """,
                (workspace_id, limit)
            )
        else:
            cur = self._conn.execute(
                """
                SELECT session_id, title, workspace_id, created_at, updated_at, full_transcript
                FROM sessions
                ORDER BY COALESCE(updated_at, created_at, rowid) DESC
                LIMIT ?
                """,
                (limit,)
            )
        results = []
        for r in cur.fetchall():
            transcript = json.loads(r["full_transcript"]) if r["full_transcript"] else []
            first_user_msg = next((m["text"] for m in transcript if m.get("role") == "user"), "")
            title = r["title"] or (first_user_msg[:38] + ("..." if len(first_user_msg) > 38 else "")) or "Oceanographic Dive"
            results.append({
                "session_id": r["session_id"],
                "title": title,
                "workspace_id": r["workspace_id"] or "",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "message_count": len(transcript)
            })
        return results

    @_serialized
    def get_session(self, session_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT session_id, title, workspace_id, created_at, updated_at, full_transcript FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if not row:
            return None
        transcript = json.loads(row["full_transcript"]) if row["full_transcript"] else []
        return {
            "session_id": row["session_id"],
            "title": row["title"],
            "workspace_id": row["workspace_id"] or "arabian",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "messages": transcript
        }

    @_serialized
    def append_transcript_message(self, session_id: str, role: str, text: str, meta: Optional[dict] = None, title: Optional[str] = None, workspace_id: str = "arabian") -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        row = self._load_row(session_id)
        existing_history = json.loads(row["history"]) if row and row["history"] else []
        existing_transcript = []
        existing_title = None
        existing_created_at = now_iso

        if row:
            cur = self._conn.execute(
                "SELECT title, full_transcript, created_at FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            full_row = cur.fetchone()
            if full_row:
                existing_transcript = json.loads(full_row["full_transcript"]) if full_row["full_transcript"] else []
                existing_title = full_row["title"]
                if full_row["created_at"]:
                    existing_created_at = full_row["created_at"]

        msg_entry = {
            "role": role,
            "text": text,
            "timestamp": now_iso,
            "meta": meta or {}
        }
        existing_transcript.append(msg_entry)

        # Synchronize multi-turn history window
        existing_history.append({"role": role, "text": text})
        del existing_history[:-MAX_TURNS_KEPT]

        if not existing_title:
            if title:
                existing_title = title
            elif role == "user":
                clean_title = text.strip()
                existing_title = clean_title[:38] + ("..." if len(clean_title) > 38 else "")
            else:
                existing_title = "Oceanographic Dive"

        self._conn.execute(
            """
            INSERT INTO sessions (session_id, history, last_context, title, workspace_id, full_transcript, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                history = excluded.history,
                title = COALESCE(sessions.title, excluded.title),
                workspace_id = COALESCE(sessions.workspace_id, excluded.workspace_id),
                full_transcript = excluded.full_transcript,
                updated_at = excluded.updated_at
            """,
            (session_id, json.dumps(existing_history), None, existing_title, workspace_id, json.dumps(existing_transcript), existing_created_at, now_iso)
        )
        self._conn.commit()
        return msg_entry

    @_serialized
    def rename_session(self, session_id: str, new_title: str) -> bool:
        cur = self._conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
            (new_title, datetime.now(timezone.utc).isoformat(), session_id)
        )
        self._conn.commit()
        return cur.rowcount > 0

    @_serialized
    def add_scheduled_task(self, task_id: str, session_id: str, prompt: str, schedule_type: str, run_at: str, interval_seconds: int = 0, coordinates: List[float] = None, persona: str = "others", workspace_id: str = "arabian") -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        coords_json = json.dumps(coordinates or [18.922, 72.833])
        self._conn.execute(
            """
            INSERT INTO scheduled_tasks (task_id, session_id, workspace_id, persona, prompt, schedule_type, run_at, interval_seconds, status, coordinates, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (task_id, session_id, workspace_id, persona, prompt, schedule_type, run_at, interval_seconds, coords_json, now_iso)
        )
        self._conn.commit()
        return {
            "task_id": task_id,
            "session_id": session_id,
            "prompt": prompt,
            "schedule_type": schedule_type,
            "run_at": run_at,
            "interval_seconds": interval_seconds,
            "status": "pending"
        }

    @_serialized
    def get_due_tasks(self, now_iso: str) -> List[dict]:
        cur = self._conn.execute(
            "SELECT * FROM scheduled_tasks WHERE status = 'pending' AND run_at <= ?",
            (now_iso,)
        )
        return [dict(r) for r in cur.fetchall()]

    @_serialized
    def mark_task_running(self, task_id: str) -> None:
        self._conn.execute(
            "UPDATE scheduled_tasks SET status = 'running' WHERE task_id = ?",
            (task_id,)
        )
        self._conn.commit()

    @_serialized
    def complete_scheduled_task(self, task_id: str, summary: str, payload: dict, next_run_at: Optional[str] = None) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        task_row = self._conn.execute("SELECT session_id, prompt FROM scheduled_tasks WHERE task_id = ?", (task_id,)).fetchone()
        session_id = task_row["session_id"] if task_row else ""
        prompt = task_row["prompt"] if task_row else ""

        if next_run_at:
            self._conn.execute(
                """
                UPDATE scheduled_tasks
                SET status = 'pending', run_at = ?, last_run = ?, result_summary = ?, result_payload = ?
                WHERE task_id = ?
                """,
                (next_run_at, now_iso, summary, json.dumps(payload), task_id)
            )
        else:
            self._conn.execute(
                """
                UPDATE scheduled_tasks
                SET status = 'completed', last_run = ?, result_summary = ?, result_payload = ?
                WHERE task_id = ?
                """,
                (now_iso, summary, json.dumps(payload), task_id)
            )

        # Record notification event for frontend polling & audio chime
        self._conn.execute(
            "INSERT INTO scheduled_task_events (task_id, session_id, prompt, summary, completed_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, session_id, prompt, summary, now_iso)
        )
        self._conn.commit()

    @_serialized
    def list_scheduled_tasks(self, session_id: Optional[str] = None) -> List[dict]:
        if session_id:
            cur = self._conn.execute(
                "SELECT * FROM scheduled_tasks WHERE session_id = ? ORDER BY rowid DESC LIMIT 50",
                (session_id,)
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM scheduled_tasks ORDER BY rowid DESC LIMIT 50"
            )
        return [dict(r) for r in cur.fetchall()]

    @_serialized
    def cancel_scheduled_task(self, task_id: str) -> bool:
        cur = self._conn.execute(
            "UPDATE scheduled_tasks SET status = 'cancelled' WHERE task_id = ?",
            (task_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    @_serialized
    def get_task_events(self, since_iso: Optional[str] = None) -> List[dict]:
        if since_iso:
            cur = self._conn.execute(
                "SELECT * FROM scheduled_task_events WHERE completed_at > ? ORDER BY event_id ASC LIMIT 50",
                (since_iso,)
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM scheduled_task_events ORDER BY event_id DESC LIMIT 10"
            )
        return [dict(r) for r in cur.fetchall()]

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
