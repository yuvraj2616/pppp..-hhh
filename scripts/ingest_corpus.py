"""Ingest every document listed in data/source_register.csv. Owner: Arnav (F4).

Run once after cloning (and after adding documents). Chroma persists to disk, so the API never
re-ingests on restart. Files are found in data/documents/ by doc_id (any supported extension).

Usage:  python scripts/ingest_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.data import db  # noqa: E402
from app.ingest import pipeline  # noqa: E402
from app.policy import source_register  # noqa: E402


def main() -> None:
    db.init_db()
    docs_dir = get_settings().documents_dir
    for meta in source_register.read_register_csv():
        matches = sorted(docs_dir.glob(f"{meta.doc_id}.*"))
        if not matches:
            print(f"SKIP {meta.doc_id}: no file in {docs_dir}")
            continue
        result = pipeline.ingest_document(matches[0], meta)
        print(f"{result.status:>12}  {meta.doc_id}  chunks={result.chunks_indexed}  rules={result.rules_extracted}")


if __name__ == "__main__":
    main()
