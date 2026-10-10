"""Runtime settings from environment variables. Shared file: change via PR only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # LLM
    mock_llm: bool = field(default_factory=lambda: _env_bool("MOCK_LLM"))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"))
    llm_timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_S", "60")))

    # Retrieval (the eval compares configurations by changing these)
    embed_model: str = field(default_factory=lambda: os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    chunk_strategy: str = field(default_factory=lambda: os.getenv("CHUNK_STRATEGY", "section"))  # section | fixed
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "6")))

    # Storage
    storage_dir: Path = field(default_factory=lambda: Path(os.getenv("STORAGE_DIR", "storage")))
    documents_dir: Path = field(default_factory=lambda: Path(os.getenv("DOCUMENTS_DIR", "data/documents")))

    @property
    def sqlite_path(self) -> Path:
        return self.storage_dir / "university.db"

    @property
    def chroma_dir(self) -> Path:
        return self.storage_dir / "chroma"

    @property
    def collection_name(self) -> str:
        """One Chroma collection per retrieval config, so configs can be compared side by side."""
        model = self.embed_model.split("/")[-1].replace(".", "-")
        return f"chunks__{model}__{self.chunk_strategy}"

    @property
    def model_label(self) -> str:
        return "mock" if self.mock_llm else f"{self.llm_provider}:{self.llm_model}"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    s.documents_dir.mkdir(parents=True, exist_ok=True)
    return s
