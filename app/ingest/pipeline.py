"""Ingestion pipeline (R11). Owner: Arnav (F4).

Contract: ingest_document(path, meta) must work while the API is running, with no restart,
and the new chunks must be searchable by the very next /ask call.

Provided: registers the source so /sources shows it immediately.
TODO (F4):
  1. parsers.extract_pages(path) -> list of (page_no, text, tables)
  2. chunking.chunk_pages(pages, strategy) -> list of chunk dicts with section + page
  3. store.upsert_chunks(meta, chunks): delete the doc's old chunks first (re-ingest = replace)
  4. rules.extractor.extract_rules(meta, chunks) (F13, Hritik) -> rules_extracted
  5. register the source with the real chunk count; return status "indexed" or "re-indexed"
"""

from __future__ import annotations

from pathlib import Path

from app.policy import source_register
from app.schemas import IngestResponse, SourceMetadata


def ingest_document(path: Path, meta: SourceMetadata) -> IngestResponse:
    existed = source_register.get_source(meta.doc_id) is not None
    # TODO (F4): parse -> chunk -> embed -> upsert; TODO (F13): extract rules
    chunks_indexed = 0
    source_register.upsert_source(meta, file_path=str(path), chunks_indexed=chunks_indexed)
    return IngestResponse(
        doc_id=meta.doc_id,
        chunks_indexed=chunks_indexed,
        status="re-registered" if existed else "registered",
    )
