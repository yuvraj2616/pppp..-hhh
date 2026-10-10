r"""LangGraph workflow. Owner: Sheel (F15).

A FIXED workflow, not a multi-agent system: the steps are known in advance and most are
deterministic. Say this in Q&A - it is what the scoring rewards.

    classify -> guard --refused--------------------------------> compose -> verify -> END
                      \--> retrieve (search + precedence) --+--> tools --> compose
                      \--> tools (personal data) -----------/
                      \--> compose (nothing to look up)

run() is the only function the API calls. It always returns a valid AskResponse and always
writes an audit record, even when a node fails (then the answer is not_found, never invented).
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone
from functools import lru_cache
from time import perf_counter

from app import audit
from app.config import get_settings
from app.graph import nodes
from app.graph.state import AssistantState
from app.schemas import (
    NOT_FOUND_MESSAGE,
    AnswerType,
    AskResponse,
    AuditRecord,
    QuestionCategory,
    SourceHit,
)

log = logging.getLogger(__name__)


@lru_cache
def build_graph():
    from langgraph.graph import END, StateGraph  # local import keeps module import light

    g = StateGraph(AssistantState)
    g.add_node("classify", nodes.classify)
    g.add_node("guard", nodes.guard)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("tools", nodes.run_tools)
    g.add_node("compose", nodes.compose)
    g.add_node("verify", nodes.verify)

    g.set_entry_point("classify")
    g.add_edge("classify", "guard")
    g.add_conditional_edges(
        "guard", nodes.route_after_guard, {"retrieve": "retrieve", "tools": "tools", "compose": "compose"}
    )
    g.add_conditional_edges("retrieve", nodes.route_after_retrieve, {"tools": "tools", "compose": "compose"})
    g.add_edge("tools", "compose")
    g.add_edge("compose", "verify")
    g.add_edge("verify", END)
    return g.compile()


def run(question: str, student_id: str | None, as_of: date) -> AskResponse:
    t0 = perf_counter()
    trace_id = audit.new_trace_id()
    state: AssistantState = {
        "trace_id": trace_id,
        "question": question,
        "student_id": student_id,
        "as_of": as_of,
        "category": QuestionCategory.unknown,
        "chunks": [],
        "tool_calls": [],
        "tool_audit": [],
        "applied_rules": [],
        "safety_flags": [],
        "llm_calls": 0,
        "tokens": 0,
    }
    try:
        final: AssistantState = build_graph().invoke(state)
        response = final["response"]
    except Exception:  # noqa: BLE001 - a failing node must never produce a fabricated answer
        if os.getenv("DEBUG_RAISE", "").lower() == "true":
            raise
        log.exception("workflow failed for trace %s", trace_id)
        final = {**state, "safety_flags": state["safety_flags"] + ["workflow_error"]}
        response = AskResponse(
            trace_id=trace_id,
            answer=NOT_FOUND_MESSAGE,
            answer_type=AnswerType.not_found,
            explanation="The assistant could not complete this request safely.",
            as_of_date=as_of.isoformat(),
        )

    resolution = final.get("resolution")
    audit.save(
        AuditRecord(
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc),
            student_id=student_id,
            question_category=final.get("category", QuestionCategory.unknown),
            sources_retrieved=[
                SourceHit(doc_id=c.doc_id, section=c.section, score=round(c.score, 3)) for c in final.get("chunks", [])
            ],
            precedence_decision=resolution.decision if resolution else None,
            tools_invoked=final.get("tool_audit", []),
            rules_applied=response.applied_rules,
            conflicts_detected=response.conflicts_detected,
            safety_flags=final.get("safety_flags", []),
            answer_type=response.answer_type,
            model=get_settings().model_label,
            llm_calls=final.get("llm_calls", 0),
            tokens=final.get("tokens", 0),
            latency_ms=int((perf_counter() - t0) * 1000),
        )
    )
    return response
