"""Annex A Source Precedence Policy (R4). Owner: Rahul (F2).

Pure Python, no LLM. Used for document chunks (Sheel's retrieve node) and for rules
(Hritik's registry). Judges test it with documents you have not seen, so it must rely
only on Source Register metadata, never on document ids you know.

Resolution order (Annex A.2):
  1. Applicability: effective_from <= as_of_date and (effective_to empty or >= as_of_date),
     and scope covers the student's programme and batch (or is ALL).
     Not-yet-effective docs are excluded from the answer but reported as upcoming.
  2. Explicit supersession: a doc that lists another doc or doc#clause in `supersedes`
     replaces it, ONLY if the superseding doc has authority level 1 or 2.
  3. Authority: lower authority_level number wins, regardless of date.
  4. Recency: same authority -> later effective_from wins.
  5. Unresolved -> Resolution.unresolved = True, both cited, answer_type conflict_flagged.
Level 5 (unofficial) can be cited as informational only and never overrides anything.
"""

from __future__ import annotations

from datetime import date

from app.schemas import Resolution, Rule, SourceMetadata


def in_scope(scope: str, value: str | int | None) -> bool:
    """TODO (F2): 'ALL' matches everything; 'B.Tech' matches 'B.Tech CSE'? decide and document;
    batches support '2023', '2023+', '2022-2024' and ';' lists. value None (general question) -> True."""
    raise NotImplementedError("F2: in_scope")


def is_effective(meta: SourceMetadata, as_of: date) -> bool:
    """TODO (F2): effective_from <= as_of <= effective_to (open-ended when effective_to is None)."""
    raise NotImplementedError("F2: is_effective")


def resolve_documents(
    docs: list[SourceMetadata],
    as_of: date,
    programme: str | None = None,
    batch: int | None = None,
    topic: str = "",
) -> Resolution:
    """Decide which of `docs` (all about the same topic) governs on `as_of`.

    Stub behaviour (until F2 lands): every doc wins, nothing is excluded. The workflow
    still runs, but conflicts are not resolved.
    TODO (F2): implement steps 1-5 above and fill decision with the step used, e.g.
    "ACAD-2026-08 supersedes ACAD-REG-2024#7.2 (step 2)".
    """
    ids = [d.doc_id for d in docs]
    return Resolution(applicable_doc_ids=ids, winner_doc_ids=ids, decision="precedence not implemented yet")


def pick_active_rule(
    rules: list[Rule],
    sources: dict[str, SourceMetadata],
    as_of: date,
    programme: str | None = None,
    batch: int | None = None,
) -> tuple[Rule | None, Resolution]:
    """Among rules for ONE parameter, return the rule that applies plus the Resolution.

    Rules inherit authority from their source document (sources[rule.source_doc_id]).
    TODO (F2): apply the same steps as resolve_documents, using the rule's own effective dates
    and scope, and the source document's authority level and supersedes list.
    """
    raise NotImplementedError("F2: pick_active_rule")
