"""Rule registry (R5). Owner: Hritik (F10).

Tools read every threshold from here, never from constants in code. A new circular that
changes a threshold becomes a new rule row (seeded or extracted on ingest); the precedence
resolver decides which row is active on the as_of_date, so old rows are never deleted.

Known parameters (extend as your documents need, and tell Sheel so routing knows them):
  min_attendance_pct           attendance needed to sit end-semester exams
  pass_marks_pct               minimum total % to pass a course
  supp_eligible_results        results that allow a supplementary attempt, e.g. "FAIL;ABSENT"
  min_cgpa_placement           CGPA cut-off for placement registration
  max_backlogs_placement       active backlogs allowed for placement
"""

from __future__ import annotations

from datetime import date

from app.data import db
from app.policy import precedence, source_register
from app.schemas import Rule


def add_rule(rule: Rule) -> None:
    """Insert or replace a rule after confirming its source is registered."""
    if source_register.get_source(rule.source_doc_id) is None:
        raise ValueError(f"unknown source document: {rule.source_doc_id}")

    row = rule.model_dump(mode="json")
    fields = list(Rule.model_fields)
    placeholders = ", ".join("?" for _ in fields)
    with db.connect() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO rule_registry ({', '.join(fields)}) VALUES ({placeholders})",
            [row[field] for field in fields],
        )


def rules_for(parameter: str) -> list[Rule]:
    """Return every registered version of a parameter in deterministic order."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT rule_id, description, parameter, operator, value, scope_programmes, "
            "scope_batches, effective_from, effective_to, source_doc_id, source_section "
            "FROM rule_registry WHERE parameter = ? ORDER BY effective_from, rule_id",
            (parameter,),
        ).fetchall()
    return [Rule.model_validate(dict(row)) for row in rows]


def active_rule(parameter: str, as_of: date, programme: str | None, batch: int | None):
    """Resolve the active rule through the Annex A precedence policy.

    None means no applicable rule: the calling tool must return UNKNOWN, never guess a threshold.
    """
    rules = rules_for(parameter)
    sources = {
        rule.source_doc_id: source
        for rule in rules
        if (source := source_register.get_source(rule.source_doc_id)) is not None
    }
    return precedence.pick_active_rule(rules, sources, as_of, programme=programme, batch=batch)
