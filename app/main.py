"""FastAPI app implementing the Section 6 contract. Owner: Rahul (F3).

Endpoints: POST /ask, POST /ingest, GET /health, GET /audit/{trace_id}, GET /sources,
POST /admin/load-students (judges may use this or scripts/load_students.py).
Everything below already runs end to end with the stubs; owners fill in the modules it calls.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError

from app import audit
from app.config import get_settings
from app.data import db
from app.graph import workflow
from app.ingest import pipeline
from app.llm import client as llm
from app.policy import source_register
from app.retrieval import store
from app.schemas import AskRequest, AskResponse, AuditRecord, HealthResponse, IngestResponse, SourceMetadata

ALLOWED_SUFFIXES = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg"}

app = FastAPI(title="University Student Services Assistant", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()  # creates tables only; never re-ingests documents (Chroma persists on disk)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, x_student_id: str | None = Header(default=None)) -> AskResponse:
    """Identity comes ONLY from the X-Student-Id header (R7), never from the question text."""
    as_of = req.as_of_date or date.today()
    return workflow.run(question=req.question, student_id=x_student_id, as_of=as_of)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), metadata: str = Form(...)) -> IngestResponse:
    """Multipart: the file + a JSON string with the Annex B Source Register fields (R11)."""
    try:
        meta = SourceMetadata.model_validate(json.loads(metadata))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid metadata: {exc}") from exc

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"unsupported file type {suffix!r}")

    target = get_settings().documents_dir / f"{meta.doc_id}{suffix}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return pipeline.ingest_document(target, meta)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    parts = {"vector_store": store.health(), "sqlite": db.health(), "llm": llm.health()}
    status = "ok" if all(v.startswith("ok") for v in parts.values()) else "degraded"
    return HealthResponse(status=status, **parts)


@app.get("/audit/{trace_id}", response_model=AuditRecord)
def get_audit(trace_id: str) -> AuditRecord:
    record = audit.get(trace_id)
    if record is None:
        raise HTTPException(status_code=404, detail="trace_id not found")
    return record


@app.get("/sources", response_model=list[SourceMetadata])
def sources() -> list[SourceMetadata]:
    return source_register.list_sources()


@app.post("/admin/load-students")
def admin_load_students(directory: str = Form(...)) -> dict:
    """Same loader as scripts/load_students.py, for judges who prefer an endpoint (F7)."""
    from scripts.load_students import load_directory  # local import: script owned by Yuvraj

    return load_directory(Path(directory))
