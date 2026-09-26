"""Small SQLite-backed document store for Researcher-mode chat retrieval."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import sqlite3
import uuid

DB_PATH = os.environ.get("SAGAR_MITRA_STORE_DB_PATH", "./data/sagar_mitra_store.db")
CHUNK_SIZE = 1400
CHUNK_OVERLAP = 180


def _connect():
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS research_sources (
            source_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
            filename TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_research_sources_workspace
            ON research_sources(workspace_id);
        CREATE TABLE IF NOT EXISTS research_source_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL, filename TEXT NOT NULL,
            chunk_index INTEGER NOT NULL, content TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_research_chunks_workspace
            ON research_source_chunks(workspace_id);
    """)
    return conn


def _split_chunks(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _extract_text(filename: str, content: bytes, suffix: str) -> str:
    if suffix == ".txt":
        return content.decode("utf-8-sig", errors="replace")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("pypdf is required to extract PDF files") from exc
    import io
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(f"[page {index + 1}] {page.extract_text() or ''}" for index, page in enumerate(reader.pages))
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc


def add_source(workspace_id: str, filename: str, content: bytes, suffix: str) -> dict:
    text = _extract_text(filename, content, suffix)
    chunks = _split_chunks(text)
    if not chunks:
        raise ValueError("No readable text was found in this file.")
    source_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO research_sources(source_id,workspace_id,filename,created_at) VALUES(?,?,?,?)",
            (source_id, workspace_id, filename, created_at),
        )
        conn.executemany(
            "INSERT INTO research_source_chunks(source_id,workspace_id,filename,chunk_index,content) VALUES(?,?,?,?,?)",
            [(source_id, workspace_id, filename, i, chunk) for i, chunk in enumerate(chunks)],
        )
    return {"id": source_id, "filename": filename, "workspace_id": workspace_id,
            "chunk_count": len(chunks), "created_at": created_at}


def list_sources(workspace_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT s.source_id AS id, s.filename, s.created_at,
                   COUNT(c.id) AS chunk_count
            FROM research_sources s LEFT JOIN research_source_chunks c USING(source_id)
            WHERE s.workspace_id=? GROUP BY s.source_id ORDER BY s.created_at DESC
        """, (workspace_id,)).fetchall()
    return [dict(row) for row in rows]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def retrieve_context(workspace_id: str, query: str, limit: int = 4) -> str:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT filename, chunk_index, content FROM research_source_chunks WHERE workspace_id=?",
            (workspace_id,),
        ).fetchall()
    if not rows:
        return ""
    query_counts = Counter(_tokens(query))
    if not query_counts:
        return ""
    docs = [Counter(_tokens(row["content"])) for row in rows]
    df = Counter(term for doc in docs for term in doc.keys())
    n = len(rows)

    def vector(counts):
        return {term: (1 + math.log(freq)) * (math.log((n + 1) / (df[term] + 1)) + 1)
                for term, freq in counts.items()}

    qv = vector(query_counts)
    qnorm = math.sqrt(sum(value * value for value in qv.values())) or 1
    scored = []
    for row, counts in zip(rows, docs):
        dv = vector(counts)
        dnorm = math.sqrt(sum(value * value for value in dv.values())) or 1
        score = sum(value * dv.get(term, 0) for term, value in qv.items()) / (qnorm * dnorm)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(
        f"[Source: {row['filename']}, chunk {row['chunk_index'] + 1}; relevance {score:.2f}]\n{row['content']}"
        for score, row in scored[:limit]
    )
