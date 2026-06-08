from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import TraceCreate, TraceResult, TraceStep


class TraceService:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS debug_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    payload TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_debug_traces_trace_id ON debug_traces(trace_id)")

    def add(self, item: TraceCreate) -> Dict[str, Any]:
        created_at = datetime.now(timezone.utc).astimezone().isoformat()
        payload = json.dumps(item.payload, ensure_ascii=False) if item.payload is not None else None
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO debug_traces(trace_id, stage, status, message, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item.trace_id, item.stage, item.status, item.message, payload, created_at),
            )
        return {"id": cur.lastrowid, "trace_id": item.trace_id, "created_at": created_at}

    def get(self, trace_id: str) -> TraceResult:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT created_at, stage, status, message, payload
                FROM debug_traces
                WHERE trace_id = ?
                ORDER BY id ASC
                """,
                (trace_id,),
            ).fetchall()
        steps: List[TraceStep] = []
        for created_at, stage, status, message, payload in rows:
            parsed_payload: Optional[Any] = None
            if payload:
                try:
                    parsed_payload = json.loads(payload)
                except ValueError:
                    parsed_payload = payload
            steps.append(
                TraceStep(
                    time=created_at,
                    stage=stage,
                    status=status,
                    message=message,
                    payload=parsed_payload,
                )
            )
        return TraceResult(trace_id=trace_id, steps=steps)
