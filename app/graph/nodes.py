"""Workflow nodes. Owner: Sheel (F15, F16).

Each node takes the state and returns ONLY the keys it changes. Keep nodes thin: the real work
lives in retrieval/, policy/, tools/, rules/, safety/ and compose.py so each owner can test it alone.
"""

from __future__ import annotations

from app.graph import compose as composer
from app.graph.state import AssistantState
from app.policy import precedence
from app.retrieval import store
from app.safety import guards
from app.schemas import QuestionCategory


# --------------------------------------------------------------------------- classify
def classify(state: AssistantState) -> dict:
    """Rules first, LLM only as a fallback.

    TODO (F15): keyword/regex rules ->
      "my attendance", "my marks/result"           -> personal_data
      "am I eligible", "can I sit", "eligible for" -> personal_eligibility
      "if I ... will I", "what if"                 -> multi_step
      "how do I", "procedure", "apply"             -> procedure
      else                                         -> policy_fact
    Then extract slots: course code/name (tools.student.find_course), what-if overrides.
    LLM fallback via llm.complete_json with a small Pydantic schema when no rule fires.
    """
    return {"category": QuestionCategory.policy_fact, "slots": {}}


# --------------------------------------------------------------------------- guard
def guard(state: AssistantState) -> dict:
    result = guards.check_request(state["question"], state.get("student_id"), state["category"])
    update: dict = {"safety_flags": state.get("safety_flags", []) + result.flags}
    if not result.allowed:
        update["refusal"] = result.message
    return update


def route_after_guard(state: AssistantState) -> str:
    if state.get("refusal"):
        return "compose"
    if state["category"] == QuestionCategory.personal_data:
        return "tools"
    return "retrieve"


# --------------------------------------------------------------------------- retrieve
def retrieve(state: AssistantState) -> dict:
    """Search, then let the Annex A resolver decide which documents govern.

    TODO (F15): pass the student's programme/batch (from tools.student.get_student_profile) when
    a header is present; resolve per topic when chunks cover different topics.
    """
    chunks = store.search(state["question"], as_of=state["as_of"])
    if not chunks:
        return {"chunks": [], "resolution": None}
    metas = {c.doc_id: c.meta for c in chunks}
    resolution = precedence.resolve_documents(list(metas.values()), state["as_of"])
    return {"chunks": chunks, "resolution": resolution}


def route_after_retrieve(state: AssistantState) -> str:
    personal = {QuestionCategory.personal_eligibility, QuestionCategory.multi_step}
    return "tools" if state["category"] in personal else "compose"


# --------------------------------------------------------------------------- tools
def run_tools(state: AssistantState) -> dict:
    """Deterministic tool plan per category - no LLM picks arbitrary tools.

    TODO (F15):
      personal_data         -> get_attendance / get_results for slots.course_code
      personal_eligibility  -> check_exam_eligibility or check_supplementary_eligibility
      multi_step / what-if  -> results + supplementary check + placement check with overrides,
                               every override recorded as an assumption
      missing/ambiguous course -> set state["clarification"]
    Append ToolCall to tool_calls, ToolAudit (status, ms, input, output) to tool_audit,
    AppliedRule to applied_rules.
    """
    return {}


# --------------------------------------------------------------------------- compose / verify
def compose(state: AssistantState) -> dict:
    return {"response": composer.compose_answer(state)}


def verify(state: AssistantState) -> dict:
    return {"response": composer.verify_answer(state, state["response"])}
