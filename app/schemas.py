"""FROZEN CONTRACT. Owner: Rahul. Changes need a PR seen by Rahul and the affected owner.

Everything that crosses a module boundary is defined here, so all six people can build
against the same types from 11:00. The /ask response mirrors Section 6.1 of the problem
statement exactly; the ingest metadata mirrors Annex B; the audit record mirrors Annex D.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

NOT_FOUND_MESSAGE = "I could not find this information in the authorised university sources."


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AnswerType(str, Enum):
    """Section 6.2 answer types. Never add a value without updating the eval set."""

    retrieved_fact = "retrieved_fact"
    calculated = "calculated"
    not_found = "not_found"
    clarification_needed = "clarification_needed"
    refused = "refused"
    conflict_flagged = "conflict_flagged"


class QuestionCategory(str, Enum):
    """Section 2.1 question kinds, used for routing and in the audit record."""

    policy_fact = "policy_fact"
    procedure = "procedure"
    personal_data = "personal_data"
    personal_eligibility = "personal_eligibility"
    multi_step = "multi_step"
    unknown = "unknown"


DocType = Literal["regulation", "circular", "notice", "faq", "handbook", "unofficial"]


# ---------------------------------------------------------------------------
# Source Register (Annex B) - also the metadata body of POST /ingest
# ---------------------------------------------------------------------------
class SourceMetadata(BaseModel):
    doc_id: str = Field(min_length=1, examples=["ACAD-REG-2024"])
    title: str
    issuer: str
    authority_level: int = Field(ge=1, le=5)
    doc_type: DocType
    version: str = ""
    effective_from: date
    effective_to: date | None = None
    supersedes: str = Field(default="", description="doc_ids or doc_id#clause, ';'-separated")
    scope_programmes: str = "ALL"
    scope_batches: str = Field(default="ALL", description="ALL, 2023, 2023+ or a ';' list")
    provenance: str = ""
    retrieved_on: date | None = None
    synthetic: Literal["Y", "N"] = "N"

    @field_validator("effective_to", "retrieved_on", mode="before")
    @classmethod
    def _empty_is_none(cls, v: Any) -> Any:
        return v or None

    def supersedes_list(self) -> list[str]:
        return [s.strip() for s in self.supersedes.split(";") if s.strip()]


class IngestResponse(BaseModel):
    doc_id: str
    chunks_indexed: int
    status: str = Field(examples=["indexed", "re-indexed", "registered", "failed"])
    rules_extracted: int = 0


# ---------------------------------------------------------------------------
# Retrieval and precedence (internal, shared by Arnav, Rahul, Hritik, Sheel)
# ---------------------------------------------------------------------------
class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    section: str | None = None
    page: int | None = None
    score: float = 0.0
    meta: SourceMetadata


class Conflict(BaseModel):
    doc_ids: list[str]
    topic: str = ""
    description: str
    resolution: str = Field(description="e.g. 'step 2 supersession: ACAD-2026-08 wins' or 'unresolved'")


class Resolution(BaseModel):
    """Output of the Annex A resolver for one question/topic."""

    applicable_doc_ids: list[str] = Field(default_factory=list)
    winner_doc_ids: list[str] = Field(default_factory=list)
    upcoming_doc_ids: list[str] = Field(default_factory=list, description="not yet effective on as_of_date")
    excluded: list[dict[str, str]] = Field(default_factory=list, description="[{doc_id, reason}]")
    conflicts: list[Conflict] = Field(default_factory=list)
    decision: str = ""
    unresolved: bool = False


# ---------------------------------------------------------------------------
# Rule registry (Annex C rule_registry table)
# ---------------------------------------------------------------------------
class Rule(BaseModel):
    rule_id: str
    description: str
    parameter: str = Field(examples=["min_attendance_pct"])
    operator: str = Field(examples=[">=", "<=", "==", "between"])
    value: str
    scope_programmes: str = "ALL"
    scope_batches: str = "ALL"
    effective_from: date
    effective_to: date | None = None
    source_doc_id: str
    source_section: str

    @field_validator("effective_to", mode="before")
    @classmethod
    def _empty_is_none(cls, v: Any) -> Any:
        return v or None


# ---------------------------------------------------------------------------
# POST /ask (Section 6, mandatory)
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    as_of_date: date | None = None


class Citation(BaseModel):
    doc_id: str
    title: str
    section: str | None = None
    page: int | None = None
    version: str | None = None
    effective_from: str | None = None


class ToolCall(BaseModel):
    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class AppliedRule(BaseModel):
    rule_id: str
    value: str
    source_doc_id: str


class AskResponse(BaseModel):
    trace_id: str
    answer: str
    answer_type: AnswerType
    citations: list[Citation] = Field(default_factory=list)
    tools_invoked: list[ToolCall] = Field(default_factory=list)
    applied_rules: list[AppliedRule] = Field(default_factory=list)
    conflicts_detected: list[Conflict] = Field(default_factory=list)
    explanation: str = ""
    as_of_date: str


# ---------------------------------------------------------------------------
# Audit (Annex D) and health
# ---------------------------------------------------------------------------
class SourceHit(BaseModel):
    doc_id: str
    section: str | None = None
    score: float = 0.0


class ToolAudit(BaseModel):
    tool: str
    status: Literal["ok", "error"] = "ok"
    ms: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    trace_id: str
    timestamp: datetime
    student_id: str | None = None
    question_category: QuestionCategory = QuestionCategory.unknown
    sources_retrieved: list[SourceHit] = Field(default_factory=list)
    precedence_decision: str | None = None
    tools_invoked: list[ToolAudit] = Field(default_factory=list)
    rules_applied: list[AppliedRule] = Field(default_factory=list)
    conflicts_detected: list[Conflict] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    answer_type: AnswerType
    model: str
    llm_calls: int = 0
    tokens: int = 0
    latency_ms: int = 0


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api: str = "ok"
    vector_store: str
    sqlite: str
    llm: str
