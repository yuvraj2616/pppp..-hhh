"""Vector store + retrieval. Owner: Arnav (F6).

ChromaDB persisted at settings.chroma_dir, one collection per config (settings.collection_name)
so the eval can compare embedding models / chunking without wiping data.
Chroma metadata cannot hold None: store empty strings and convert back.

Retrieval does NOT filter by effective date: the precedence resolver needs to see
superseded and upcoming documents to explain them. It DOES filter by programme/batch scope.
"""

from __future__ import annotations

from datetime import date

from app.config import get_settings
from app.schemas import Chunk, SourceMetadata


def health() -> str:
    """'ok' when the persisted collection can be opened (or 'ok' in MOCK mode with no store yet)."""
    s = get_settings()
    try:
        import chromadb  # noqa: F401 - heavy import kept local
    except ImportError:
        return "ok (chromadb not installed: mock mode)" if s.mock_llm else "error: chromadb not installed"
    # TODO (F6): open the PersistentClient and collection, return "ok" or the error text
    return "ok"


def upsert_chunks(meta: SourceMetadata, chunks: list) -> int:
    """TODO (F6): delete existing chunks where doc_id == meta.doc_id, embed and add new ones.

    ids: f"{doc_id}::{i}", metadata: all SourceMetadata fields + section + page + kind.
    Return the number of chunks written.
    """
    raise NotImplementedError("F6: upsert_chunks")


def search(
    query: str,
    *,
    as_of: date,
    programme: str | None = None,
    batch: int | None = None,
    k: int | None = None,
) -> list[Chunk]:
    """Top-k chunks for `query`, best first, score = similarity in [0, 1].

    Stub: returns [] so the workflow answers not_found until F6 lands (safe default, R3).
    TODO (F6): query k*2, drop out-of-scope chunks (precedence.in_scope), return the top k.
    """
    return []
