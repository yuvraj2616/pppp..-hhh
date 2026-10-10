"""SQLite access layer. Owner: Yuvraj (F7).

Provided: connect() and init_db() so the stack boots.
TODO (F7): upsert helpers used by scripts/load_students.py and the /admin loader.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path

from app.config import get_settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
REQUIRED_TABLES = ("students", "courses", "attendance", "results", "rule_registry")
ALLOWED_TABLES = frozenset(REQUIRED_TABLES)
TABLE_COLUMNS = {
    "students": ("student_id", "full_name", "programme", "batch_year", "current_semester", "cgpa", "active_backlogs"),
    "courses": ("course_code", "course_name", "programme", "semester", "credits"),
    "attendance": ("student_id", "course_code", "classes_held", "classes_attended"),
    "results": (
        "student_id", "course_code", "exam_session", "exam_type", "internal_marks", "external_marks",
        "total_marks", "max_marks", "result",
    ),
    "rule_registry": (
        "rule_id", "description", "parameter", "operator", "value", "scope_programmes", "scope_batches",
        "effective_from", "effective_to", "source_doc_id", "source_section",
    ),
}


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the database with row access by column name and foreign keys on."""
    db_path = path or get_settings().sqlite_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path | None = None) -> None:
    """Create all tables if missing. Safe to call on every start (no data is touched)."""
    with connect(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def health() -> str:
    try:
        with connect() as conn:
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in REQUIRED_TABLES if t not in names]
        return "ok" if not missing else f"missing tables: {', '.join(missing)}"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return f"error: {exc}"


def upsert_rows(table: str, rows: Iterable[Mapping[str, object]]) -> int:
    """Insert rows into an allowed table in one transaction and return the count written.

    Empty strings become ``NULL`` so nullable CSV fields are stored correctly.
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"table is not allowed: {table}")

    materialized = list(rows)
    if not materialized:
        return 0
    allowed_columns = set(TABLE_COLUMNS[table])
    with connect() as conn:
        for row in materialized:
            columns = list(row.keys())
            unknown = [column for column in columns if column not in allowed_columns]
            if unknown:
                raise ValueError(f"unknown columns for {table}: {', '.join(map(str, unknown))}")
            if not columns:
                raise ValueError("row must contain at least one column")
            values = [None if row[column] == "" else row[column] for column in columns]
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
    return len(materialized)
