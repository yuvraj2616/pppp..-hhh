"""Workflow state shared by all nodes. Owner: Sheel. Add keys freely; never remove them."""

from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

from app.schemas import AppliedRule, AskResponse, Chunk, QuestionCategory, Resolution, ToolAudit, ToolCall


class AssistantState(TypedDict, total=False):
    trace_id: str
    question: str
    student_id: str | None  # ONLY from the X-Student-Id header
    as_of: date
    category: QuestionCategory
    slots: dict[str, Any]  # e.g. {"course_code": "CS201", "what_if": {"active_backlogs": 0}}
    profile: dict[str, Any]
    chunks: list[Chunk]
    resolution: Resolution | None
    tool_calls: list[ToolCall]
    tool_audit: list[ToolAudit]
    applied_rules: list[AppliedRule]
    safety_flags: list[str]
    refusal: str | None
    clarification: str | None
    response: AskResponse
    llm_calls: int
    tokens: int
