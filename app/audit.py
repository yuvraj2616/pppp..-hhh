"""Audit store (R10). Owner: Rahul (F3).

Provided: save/get backed by the audit_log table.
TODO (F3): keep only what the audit needs (no question text, R7); add GET /audit samples to docs/audit_samples/.
"""

from __future__ import annotations

import uuid

from app.data import db
from app.schemas import AuditRecord


def new_trace_id() -> str:
    return uuid.uuid4().hex[:8]


def save(record: AuditRecord) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO audit_log (trace_id, timestamp, student_id, record_json) VALUES (?, ?, ?, ?)",
            (record.trace_id, record.timestamp.isoformat(), record.student_id, record.model_dump_json()),
        )


def get(trace_id: str) -> AuditRecord | None:
    with db.connect() as conn:
        row = conn.execute("SELECT record_json FROM audit_log WHERE trace_id = ?", (trace_id,)).fetchone()
    return AuditRecord.model_validate_json(row["record_json"]) if row else None
