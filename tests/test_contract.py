"""Section 6 contract tests. Owner: Rahul. These must pass on every PR - they are what judges hit live."""

from __future__ import annotations

import json

from app.schemas import NOT_FOUND_MESSAGE, AnswerType

RESPONSE_KEYS = {
    "trace_id", "answer", "answer_type", "citations", "tools_invoked",
    "applied_rules", "conflicts_detected", "explanation", "as_of_date",
}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert {"status", "vector_store", "sqlite", "llm"} <= r.json().keys()


def test_ask_returns_contract_shape(client):
    r = client.post("/ask", json={"question": "What is the scholarship for studying in Antarctica?",
                                  "as_of_date": "2026-10-06"})
    assert r.status_code == 200
    body = r.json()
    assert RESPONSE_KEYS <= body.keys()
    assert body["answer_type"] in {t.value for t in AnswerType}
    assert body["as_of_date"] == "2026-10-06"


def test_unanswerable_is_not_found_with_exact_message(client):
    body = client.post("/ask", json={"question": "What is the scholarship for studying in Antarctica?"}).json()
    assert body["answer_type"] == "not_found"
    assert body["answer"] == NOT_FOUND_MESSAGE


def test_every_answer_has_an_audit_record(client):
    body = client.post("/ask", json={"question": "Minimum attendance?"}, headers={"X-Student-Id": "S1001"}).json()
    audit = client.get(f"/audit/{body['trace_id']}")
    assert audit.status_code == 200
    record = audit.json()
    assert record["trace_id"] == body["trace_id"]
    assert {"sources_retrieved", "tools_invoked", "model", "latency_ms", "tokens"} <= record.keys()


def test_unknown_audit_is_404(client):
    assert client.get("/audit/doesnotexist").status_code == 404


def test_ingest_registers_source_and_sources_lists_it(client, sample_metadata):
    files = {"file": ("reg.txt", b"7.2 Minimum attendance is 75%.", "text/plain")}
    r = client.post("/ingest", files=files, data={"metadata": json.dumps(sample_metadata)})
    assert r.status_code == 200, r.text
    assert {"doc_id", "chunks_indexed", "status"} <= r.json().keys()
    ids = [s["doc_id"] for s in client.get("/sources").json()]
    assert "TEST-REG-2024" in ids


def test_ingest_rejects_bad_metadata(client, sample_metadata):
    bad = {**sample_metadata, "authority_level": 9}
    files = {"file": ("reg.txt", b"text", "text/plain")}
    r = client.post("/ingest", files=files, data={"metadata": json.dumps(bad)})
    assert r.status_code == 422
