"""Answer composer + citation verifier (R2, R3, R9). Owner: Sheel (F17).

answer_type selection (Section 6.2):
  refusal set                         -> refused
  clarification set                   -> clarification_needed
  resolution.unresolved               -> conflict_flagged (cite BOTH documents)
  tool results drive the answer       -> calculated
  answer comes from winning chunks    -> retrieved_fact
  no evidence                         -> not_found with NOT_FOUND_MESSAGE exactly

The LLM only words `answer` and `explanation` from the evidence it is given (winning chunks,
tool outputs, applied rules) and must reference evidence ids. Citations are built in CODE from
the chunks it referenced - the LLM never types a doc_id, page or date.
"""

from __future__ import annotations

from app.graph.state import AssistantState
from app.schemas import NOT_FOUND_MESSAGE, AnswerType, AskResponse


def _base(state: AssistantState) -> dict:
    return {
        "trace_id": state["trace_id"],
        "as_of_date": state["as_of"].isoformat(),
        "tools_invoked": state.get("tool_calls", []),
        "applied_rules": state.get("applied_rules", []),
        "conflicts_detected": state["resolution"].conflicts if state.get("resolution") else [],
    }


def compose_answer(state: AssistantState) -> AskResponse:
    if state.get("refusal"):
        return AskResponse(
            **_base(state), answer=state["refusal"], answer_type=AnswerType.refused,
            explanation="This request is not allowed for the current identity.",
        )
    if state.get("clarification"):
        return AskResponse(**_base(state), answer=state["clarification"], answer_type=AnswerType.clarification_needed)
    if not state.get("chunks") and not state.get("tool_calls"):
        return AskResponse(**_base(state), answer=NOT_FOUND_MESSAGE, answer_type=AnswerType.not_found)

    # TODO (F17): build the evidence prompt, call llm.complete_json, build citations from the
    # referenced chunk ids, choose answer_type as above, mention upcoming docs and partial evidence.
    return AskResponse(**_base(state), answer=NOT_FOUND_MESSAGE, answer_type=AnswerType.not_found)


def verify_answer(state: AssistantState, response: AskResponse) -> AskResponse:
    """TODO (F17): every citation must come from a retrieved chunk whose text contains the cited value;
    every number in the answer must appear in a tool output or a cited chunk. On failure downgrade to
    not_found (no evidence left) or state clearly what is known and what is not (partial)."""
    return response
