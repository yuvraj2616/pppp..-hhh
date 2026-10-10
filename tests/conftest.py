"""Shared fixtures. Every test runs with MOCK_LLM=true and a throwaway storage folder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("DOCUMENTS_DIR", str(tmp_path / "documents"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.data import db

    db.init_db()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_metadata() -> dict:
    return {
        "doc_id": "TEST-REG-2024",
        "title": "Test Academic Regulations",
        "issuer": "Office of the Dean (Academics)",
        "authority_level": 1,
        "doc_type": "regulation",
        "version": "1.0",
        "effective_from": "2024-07-01",
        "effective_to": "",
        "supersedes": "",
        "scope_programmes": "ALL",
        "scope_batches": "ALL",
        "provenance": "test fixture",
        "retrieved_on": "2026-10-05",
        "synthetic": "Y",
    }


os.environ.setdefault("MOCK_LLM", "true")
