"""LLM client. Owner: Sheel (F14).

One place that talks to the model, so the rest of the code never cares which provider runs.
  - provider "ollama" (default): POST {OLLAMA_BASE_URL}/api/chat with stream=false and
    format=<JSON schema of the Pydantic model> for structured output.
  - MOCK_LLM=true: deterministic canned outputs, no network (CI, tests, demo fallback).
  - provider "openai"/"anthropic": cloud fallback ONLY behind LLM_PROVIDER, disclosed in README.
Local 7-8B models break JSON sometimes: validate with Pydantic, retry up to 2 times with the
validation error appended, then raise LLMError so the caller can fall back (never invent output).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    models: list[str] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def complete_json(system: str, user: str, schema: type[T], usage: Usage | None = None) -> T:
    """Return a validated instance of `schema`. Add token counts to `usage` (prompt_eval_count/eval_count).

    TODO (F14): mock branch (build a minimal valid instance deterministically), Ollama branch with
    retries, cloud branch behind LLM_PROVIDER.
    """
    raise NotImplementedError("F14: complete_json")


def complete_text(system: str, user: str, usage: Usage | None = None) -> str:
    """TODO (F14): plain text completion (used only for wording explanations from evidence)."""
    raise NotImplementedError("F14: complete_text")


def health() -> str:
    s = get_settings()
    if s.mock_llm:
        return "ok (mock)"
    # TODO (F14): GET {ollama_base_url}/api/tags with a 2 s timeout; check s.llm_model is pulled
    return "unknown (health check not implemented)"
