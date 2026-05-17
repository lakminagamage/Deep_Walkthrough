from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from app.config import SQLITE_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    summary     TEXT,
    status      TEXT NOT NULL,
    created_at  TIMESTAMP,
    completed_at TIMESTAMP,
    report_id   TEXT
);

CREATE TABLE IF NOT EXISTS session_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    agent       TEXT,
    payload     TEXT,
    timestamp   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hitl_decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    gate        TEXT NOT NULL,
    decision    TEXT NOT NULL,
    payload     TEXT,
    timestamp   TIMESTAMP
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EpisodicMemory:
    def __init__(self, db_path: str = SQLITE_PATH) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(_SCHEMA)
            # Migrate existing tables that predate the summary column.
            try:
                await db.execute("ALTER TABLE sessions ADD COLUMN summary TEXT")
            except Exception:
                pass  # Column already exists
            await db.commit()

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def create_session(self, session_id: str, query: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO sessions (id, query, status, created_at) VALUES (?, ?, ?, ?)",
                (session_id, query, "running", _now()),
            )
            await db.commit()

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        report_id: str | None = None,
    ) -> None:
        completed_at = _now() if status in ("complete", "error") else None
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE sessions SET status=?, completed_at=?, report_id=? WHERE id=?",
                (status, completed_at, report_id, session_id),
            )
            await db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    # ── Events ────────────────────────────────────────────────────────────────

    async def log_event(
        self,
        session_id: str,
        event_type: str,
        agent: str | None = None,
        payload: dict | None = None,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO session_events (session_id, event_type, agent, payload, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (session_id, event_type, agent, json.dumps(payload) if payload else None, _now()),
            )
            await db.commit()

    async def get_session_events(self, session_id: str) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM session_events WHERE session_id=? ORDER BY timestamp",
                (session_id,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def delete_session(self, session_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM hitl_decisions  WHERE session_id=?", (session_id,))
            await db.execute("DELETE FROM session_events  WHERE session_id=?", (session_id,))
            await db.execute("DELETE FROM sessions        WHERE id=?",         (session_id,))
            await db.commit()

    async def update_session_summary(self, session_id: str, summary: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE sessions SET summary=? WHERE id=?", (summary, session_id)
            )
            await db.commit()

    async def list_sessions(self, limit: int = 30) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # ── HITL decisions ────────────────────────────────────────────────────────

    async def log_hitl_decision(
        self,
        session_id: str,
        gate: str,
        decision: str,
        payload: dict | None = None,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO hitl_decisions (session_id, gate, decision, payload, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (session_id, gate, decision, json.dumps(payload) if payload else None, _now()),
            )
            await db.commit()
