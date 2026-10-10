"""Source Register (Annex B). Owner: Rahul (F1).

Provided: upsert/get/list over the `sources` table so /ingest and /sources work.
TODO (F1):
  - sync_from_csv(): load data/source_register.csv into the table at startup (idempotent).
  - export_csv(): write the table back to data/source_register.csv (deliverable).
  - Validate that every `supersedes` target exists or log a warning.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from app.data import db
from app.schemas import SourceMetadata

REGISTER_CSV = Path("data/source_register.csv")
FIELDS = list(SourceMetadata.model_fields)


def upsert_source(meta: SourceMetadata, file_path: str | None = None, chunks_indexed: int = 0) -> None:
    row = meta.model_dump(mode="json")
    with db.connect() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO sources ({', '.join(FIELDS)}, file_path, chunks_indexed, ingested_at) "
            f"VALUES ({', '.join('?' for _ in FIELDS)}, ?, ?, ?)",
            [row[f] for f in FIELDS] + [file_path, chunks_indexed, datetime.now(timezone.utc).isoformat()],
        )


def get_source(doc_id: str) -> SourceMetadata | None:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM sources WHERE doc_id = ?", (doc_id,)).fetchone()
    return SourceMetadata.model_validate({f: row[f] for f in FIELDS}) if row else None


def list_sources() -> list[SourceMetadata]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY authority_level, effective_from").fetchall()
    return [SourceMetadata.model_validate({f: r[f] for f in FIELDS}) for r in rows]


def read_register_csv(path: Path = REGISTER_CSV) -> list[SourceMetadata]:
    """Parse the CSV deliverable into validated metadata rows."""
    with path.open(newline="", encoding="utf-8") as fh:
        return [SourceMetadata.model_validate(r) for r in csv.DictReader(fh) if r.get("doc_id")]


def sync_from_csv(path: Path = REGISTER_CSV) -> int:
    """TODO (F1): upsert every CSV row that is not already registered; return count."""
    raise NotImplementedError("F1: sync_from_csv")
