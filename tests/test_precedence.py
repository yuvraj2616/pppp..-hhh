"""Annex A tests. Owner: Rahul (F2). Remove the xfail marker when F2 lands - then these gate every merge."""

from __future__ import annotations

from datetime import date

import pytest

from app.policy import precedence
from app.schemas import SourceMetadata

pytestmark = pytest.mark.xfail(reason="F2 precedence not implemented yet", strict=False)

AS_OF = date(2026, 10, 6)


def meta(doc_id, level, doc_type, eff_from, supersedes="", eff_to=None, programmes="ALL", batches="ALL"):
    return SourceMetadata(
        doc_id=doc_id, title=doc_id, issuer="x", authority_level=level, doc_type=doc_type,
        effective_from=eff_from, effective_to=eff_to, supersedes=supersedes,
        scope_programmes=programmes, scope_batches=batches,
    )


REG = meta("ACAD-REG-2024", 1, "regulation", "2024-07-01")
CIRC = meta("ACAD-2026-08", 2, "circular", "2026-08-01", supersedes="ACAD-REG-2024#7.2")
FAQ = meta("DEPT-FAQ", 4, "faq", "2026-09-15")


def test_annex_a_worked_example():
    res = precedence.resolve_documents([REG, CIRC, FAQ], AS_OF, topic="minimum attendance")
    assert res.winner_doc_ids == ["ACAD-2026-08"]
    assert not res.unresolved
    assert "step 2" in res.decision
    assert any("DEPT-FAQ" in c.doc_ids for c in res.conflicts)  # FAQ conflict is noted


def test_not_yet_effective_is_upcoming_not_current():
    future = meta("ACAD-2026-11", 2, "circular", "2026-11-01", supersedes="ACAD-REG-2024#7.2")
    res = precedence.resolve_documents([REG, future], AS_OF)
    assert res.winner_doc_ids == ["ACAD-REG-2024"]
    assert res.upcoming_doc_ids == ["ACAD-2026-11"]


def test_supersession_needs_authority_1_or_2():
    notice = meta("DEPT-NOTICE", 3, "notice", "2026-09-01", supersedes="ACAD-REG-2024#7.2")
    res = precedence.resolve_documents([REG, notice], AS_OF)
    assert res.winner_doc_ids == ["ACAD-REG-2024"]  # step 3: authority beats date


def test_same_authority_later_date_wins():
    old = meta("CIRC-A", 2, "circular", "2025-01-01")
    new = meta("CIRC-B", 2, "circular", "2026-01-01")
    assert precedence.resolve_documents([old, new], AS_OF).winner_doc_ids == ["CIRC-B"]


def test_unofficial_never_overrides():
    forum = meta("FORUM-POST", 5, "unofficial", "2026-10-01")
    assert precedence.resolve_documents([REG, forum], AS_OF).winner_doc_ids == ["ACAD-REG-2024"]


def test_scope_excludes_other_programme_and_batch():
    mtech = meta("MTECH-CIRC", 2, "circular", "2026-01-01", programmes="M.Tech")
    res = precedence.resolve_documents([REG, mtech], AS_OF, programme="B.Tech CSE", batch=2023)
    assert res.winner_doc_ids == ["ACAD-REG-2024"]
    assert precedence.in_scope("2023+", 2024) and not precedence.in_scope("2023+", 2022)


def test_expired_document_is_not_applicable():
    expired = meta("OLD-CIRC", 2, "circular", "2023-01-01", eff_to="2024-06-30")
    assert "OLD-CIRC" not in precedence.resolve_documents([REG, expired], AS_OF).applicable_doc_ids
