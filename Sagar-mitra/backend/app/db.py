"""
Sagar Mitra / ORCA - Persistent Store (SQLite)
====================================================
Phase 0 #1: a persistent, on-disk store for data that must survive a
process restart -- unlike app/data.py's DataStore (in-memory pandas,
rebuilt from the parquet on every startup) and app/session_store.py
(in-memory dict, lost on restart).

This module is deliberately ADDITIVE, not a replacement: app/data.py's
pandas-based DataStore keeps working exactly as before (every existing
caller of `from app.data import store` is untouched), and this module
loads the SAME final_dataset.parquet into a SQLite table alongside it, for
callers that want to run a filtered/aggregated SQL query without pandas
re-reading and re-scanning the whole parquet file in memory each time
(e.g. the geofence/SOS logging path in Task 2, or an ad-hoc bbox lookup).

SQLite (stdlib `sqlite3`) was chosen over DuckDB because it needs no new
dependency beyond what's already in requirements.txt (pandas' `to_sql`/
`read_sql` already talk to it directly), which is the least-friction fit
for this pandas-based pipeline.

Two tables live in this DB file:
  - argo_readings: a straight copy of final_dataset.parquet, indexed on
    (LATITUDE, LONGITUDE) for range queries.
  - sos_events: mayday/SOS log rows written by POST /api/sos (Task 2).
"""
import os
import sqlite3
from typing import Optional

import pandas as pd

# Same relative-path convention app/data.py's DATA_PATH uses -- both assume
# the process is started from the backend/ directory (see README: `uvicorn
# app.main:app ...` run from backend/), overridable via env var for anyone
# running from elsewhere.
DB_PATH = os.environ.get("SAGAR_MITRA_DB_PATH", "./data/sagar_mitra.db")
PARQUET_PATH = os.environ.get("SAGAR_MITRA_DATA_PATH", "./data/final_dataset.parquet")

ARGO_TABLE = "argo_readings"
SOS_TABLE = "sos_events"


def get_connection() -> sqlite3.Connection:
    """New connection per call -- sqlite3 connections aren't safe to share
    across threads, and FastAPI's threadpool-per-request means callers can
    come from different threads. Cheap enough to open per call for this
    hackathon's request volume."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _table_row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0  # table doesn't exist yet


def init_argo_table(conn: Optional[sqlite3.Connection] = None) -> None:
    """Loads final_dataset.parquet into argo_readings if the table is
    missing or empty. Safe to call on every startup: once populated, this
    is a cheap COUNT(*) no-op rather than a full reload."""
    own_conn = conn is None
    conn = conn or get_connection()
    try:
        if _table_row_count(conn, ARGO_TABLE) > 0:
            return
        if not os.path.exists(PARQUET_PATH):
            print(f"[db] {PARQUET_PATH} not found -- skipping SQLite argo_readings load.")
            return
        df = pd.read_parquet(PARQUET_PATH)
        df.to_sql(ARGO_TABLE, conn, if_exists="replace", index=False)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_argo_latlon ON {ARGO_TABLE} (LATITUDE, LONGITUDE)")
        conn.commit()
        print(f"[db] Loaded {len(df)} rows into {ARGO_TABLE} ({DB_PATH})")
    finally:
        if own_conn:
            conn.close()


def init_sos_table(conn: Optional[sqlite3.Connection] = None) -> None:
    own_conn = conn is None
    conn = conn or get_connection()
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {SOS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                hazard_status TEXT,
                nearest_port TEXT,
                message TEXT,
                session_id TEXT,
                raw_payload TEXT
            )
        """)
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def init_db() -> None:
    """Called once at FastAPI startup (see main.py)."""
    conn = get_connection()
    try:
        init_argo_table(conn)
        init_sos_table(conn)
    finally:
        conn.close()


# --- Query helpers --------------------------------------------------------

def count_argo_rows() -> int:
    conn = get_connection()
    try:
        return _table_row_count(conn, ARGO_TABLE)
    finally:
        conn.close()


def query_argo_bbox(lat_min: float, lat_max: float, lon_min: float, lon_max: float,
                     limit: int = 500) -> pd.DataFrame:
    """Rows within a lat/lon bounding box, straight from SQLite -- no full
    parquet re-read/re-scan in pandas (see app/data.py's DataStore methods,
    which do exactly that scan on every call)."""
    conn = get_connection()
    try:
        return pd.read_sql(
            f"SELECT * FROM {ARGO_TABLE} WHERE LATITUDE BETWEEN ? AND ? "
            f"AND LONGITUDE BETWEEN ? AND ? LIMIT ?",
            conn, params=[lat_min, lat_max, lon_min, lon_max, limit],
        )
    finally:
        conn.close()


# --- SOS event log (Task 2) ------------------------------------------------

def insert_sos_event(event: dict) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            f"INSERT INTO {SOS_TABLE} "
            f"(timestamp, lat, lon, hazard_status, nearest_port, message, session_id, raw_payload) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event["timestamp"], event["lat"], event["lon"],
                event.get("hazard_status"), event.get("nearest_port"),
                event.get("message"), event.get("session_id"), event.get("raw_payload"),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_sos_events(limit: int = 100) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(
            f"SELECT * FROM {SOS_TABLE} ORDER BY id DESC LIMIT ?", conn, params=[limit],
        )
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"argo_readings row count: {count_argo_rows()}")
    print(query_argo_bbox(14.0, 20.0, 68.0, 74.0, limit=5))
