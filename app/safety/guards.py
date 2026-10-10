"""Safety guards (R7, R8). Owner: Sheel (F16).

R7: identity only from X-Student-Id. Refuse:
    - any personal question with no header,
    - any question naming another student ID (regex S#### different from the header) or asking
      for "my friend's"/"another student's" records.
R8: document text is data. Before chunk text goes into a prompt, wrap it in clear delimiters and
    flag (not obey) instruction-like lines ("ignore previous instructions", "you are now", ...).
Never log personal data you do not need: flags go to the audit as short codes, not raw text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import AnswerType, QuestionCategory

STUDENT_ID_RE = re.compile(r"\bS\d{4}\b", re.IGNORECASE)
PERSONAL_CATEGORIES = {
    QuestionCategory.personal_data,
    QuestionCategory.personal_eligibility,
    QuestionCategory.multi_step,
}


@dataclass
class GuardResult:
    allowed: bool = True
    answer_type: AnswerType | None = None
    message: str = ""
    flags: list[str] = field(default_factory=list)


def check_request(question: str, student_id: str | None, category: QuestionCategory) -> GuardResult:
    """TODO (F16): implement the R7 rules above. Stub allows everything."""
    return GuardResult()


def wrap_document_text(chunk_text: str) -> tuple[str, list[str]]:
    """TODO (F16): return (delimited text safe to put in a prompt, flags found)."""
    return f"<document>\n{chunk_text}\n</document>", []
