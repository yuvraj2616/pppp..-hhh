"""R5 tool tests. Owners: Hritik (tools), Yuvraj (db). Remove xfail as each feature lands.

The fixture writes a tiny dataset straight into SQLite so tools can be tested without the generator.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.data import db
from app.schemas import Rule, SourceMetadata

AS_OF = date(2026, 10, 6)


@pytest.fixture
def tiny_db():
    with db.connect() as conn:
        conn.execute("INSERT INTO students VALUES ('S1001','Test One','B.Tech CSE',2023,5,8.1,0)")
        conn.execute("INSERT INTO courses VALUES ('CS201','Data Structures','B.Tech CSE',3,4)")
        conn.execute("INSERT INTO attendance VALUES ('S1001','CS201',40,30)")  # exactly 75%
        conn.execute(
            "INSERT INTO sources (doc_id,title,issuer,authority_level,doc_type,effective_from,scope_programmes,"
            "scope_batches,synthetic) VALUES ('REG','Regs','Dean',1,'regulation','2024-07-01','ALL','ALL','N')"
        )
        conn.execute(
            "INSERT INTO rule_registry VALUES ('ATT-MIN-01','Minimum attendance','min_attendance_pct','>=','75',"
            "'ALL','ALL','2024-07-01',NULL,'REG','7.2')"
        )


def test_attendance_pct_is_computed_by_code(tiny_db):
    from app.tools.student import get_attendance

    out, call = get_attendance("S1001", "CS201")
    assert out["attendance_pct"] == 75.0
    assert call.tool == "get_attendance"


def test_unknown_course_raises_lookup_error(tiny_db):
    from app.tools.student import get_attendance

    with pytest.raises(LookupError):
        get_attendance("S1001", "CS999")


def test_ambiguous_course_name_returns_all_matches(tiny_db):
    from app.tools.student import find_course

    with db.connect() as conn:
        conn.execute("INSERT INTO courses VALUES ('CS202','Advanced Data Structures','B.Tech CSE',4,4)")

    matches = find_course("S1001", "data structures")
    assert [course["course_code"] for course in matches] == ["CS201", "CS202"]


def test_absent_result_is_returned(tiny_db):
    from app.tools.student import get_results

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO results VALUES "
            "('S1001','CS201','2026-10','REGULAR',NULL,NULL,NULL,100,'ABSENT')"
        )

    out, call = get_results("S1001", "CS201")
    assert out["results"][0]["result"] == "ABSENT"
    assert call.tool == "get_results"


def test_exactly_at_threshold_is_eligible(tiny_db):
    from app.tools.eligibility import check_exam_eligibility

    out, _, rules = check_exam_eligibility("S1001", "CS201", AS_OF)
    assert out["result"] == "ELIGIBLE"
    assert rules[0].rule_id == "ATT-MIN-01"


def test_threshold_comes_from_registry_not_code(tiny_db):
    from app.tools.eligibility import check_exam_eligibility

    with db.connect() as conn:
        conn.execute("UPDATE rule_registry SET value='80' WHERE rule_id='ATT-MIN-01'")
    out, _, _ = check_exam_eligibility("S1001", "CS201", AS_OF)
    assert out["result"] == "NOT_ELIGIBLE"


def test_one_class_below_threshold_is_not_eligible(tiny_db):
    from app.tools.eligibility import check_exam_eligibility

    with db.connect() as conn:
        conn.execute(
            "UPDATE attendance SET classes_attended = 29 WHERE student_id = 'S1001' AND course_code = 'CS201'"
        )
    out, _, _ = check_exam_eligibility("S1001", "CS201", AS_OF)
    assert out["actual"] == 72.5
    assert out["result"] == "NOT_ELIGIBLE"


def test_missing_rule_returns_unknown(tiny_db):
    from app.tools.eligibility import check_placement_eligibility

    out, _, applied = check_placement_eligibility("S1001", AS_OF)
    assert out["result"] == "UNKNOWN"
    assert applied == []


def test_compare_supports_all_registry_operators():
    from app.tools.eligibility import compare

    assert compare(75, ">=", "75")
    assert compare(75, "<=", "75")
    assert compare(76, ">", "75")
    assert compare(74, "<", "75")
    assert compare(75, "==", "75")
    assert compare(75, "between", "70;80")
    assert compare("ABSENT", "in", "FAIL;ABSENT")


def test_detained_result_is_not_supplementary_eligible(tiny_db):
    from app.rules import registry
    from app.schemas import Rule
    from app.tools.eligibility import check_supplementary_eligibility

    registry.add_rule(Rule(
        rule_id="SUP-ELIG-01", description="Supplementary results", parameter="supp_eligible_results",
        operator="in", value="FAIL;ABSENT", effective_from=date(2024, 7, 1), source_doc_id="REG",
        source_section="Clause 8.1, p. 5",
    ))
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO results VALUES "
            "('S1001','CS201','2026-10','REGULAR',20,0,20,100,'DETAINED')"
        )
    out, _, applied = check_supplementary_eligibility("S1001", "CS201", AS_OF)
    assert out["result"] == "NOT_ELIGIBLE"
    assert applied[0].rule_id == "SUP-ELIG-01"


def test_placement_accepts_cgpa_exactly_at_cutoff(tiny_db):
    from app.rules import registry
    from app.schemas import Rule
    from app.tools.eligibility import check_placement_eligibility

    registry.add_rule(Rule(
        rule_id="PLC-CGPA-01", description="Placement CGPA", parameter="min_cgpa_placement",
        operator=">=", value="8.1", effective_from=date(2024, 7, 1), source_doc_id="REG",
        source_section="Clause 9.1, p. 6",
    ))
    registry.add_rule(Rule(
        rule_id="PLC-BACK-01", description="Placement backlogs", parameter="max_backlogs_placement",
        operator="<=", value="0", effective_from=date(2024, 7, 1), source_doc_id="REG",
        source_section="Clause 9.1, p. 6",
    ))
    out, _, _ = check_placement_eligibility("S1001", AS_OF)
    assert out["result"] == "ELIGIBLE"


def test_placement_what_if_clears_backlogs(tiny_db):
    from app.rules import registry
    from app.schemas import Rule
    from app.tools.eligibility import check_placement_eligibility

    registry.add_rule(Rule(
        rule_id="PLC-CGPA-01", description="Placement CGPA", parameter="min_cgpa_placement",
        operator=">=", value="8.0", effective_from=date(2024, 7, 1), source_doc_id="REG",
        source_section="Clause 9.1, p. 6",
    ))
    registry.add_rule(Rule(
        rule_id="PLC-BACK-01", description="Placement backlogs", parameter="max_backlogs_placement",
        operator="<=", value="0", effective_from=date(2024, 7, 1), source_doc_id="REG",
        source_section="Clause 9.1, p. 6",
    ))
    with db.connect() as conn:
        conn.execute("UPDATE students SET active_backlogs = 2 WHERE student_id = 'S1001'")
    out, _, _ = check_placement_eligibility("S1001", AS_OF, overrides={"active_backlogs": 0})
    assert out["result"] == "ELIGIBLE"
    assert "active_backlogs=0" in out["assumptions"]


def test_rule_registry_delegates_superseded_rule_resolution(tiny_db, monkeypatch):
    from app.policy import source_register
    from app.rules import registry
    from app.schemas import Resolution

    source_register.upsert_source(
        SourceMetadata(
            doc_id="REG-NEW", title="New", issuer="Dean", authority_level=2,
            doc_type="circular", version="2", effective_from=date(2026, 8, 1),
        )
    )
    registry.add_rule(Rule(
        rule_id="ATT-MIN-02", description="Updated attendance", parameter="min_attendance_pct",
        operator=">=", value="80", effective_from=date(2026, 8, 1), source_doc_id="REG-NEW",
        source_section="Clause 7.2, p. 3",
    ))
    captured = {}

    def fake_pick(rules, sources, as_of, programme=None, batch=None):
        captured["rules"] = rules
        captured["sources"] = sources
        return rules[-1], Resolution(winner_doc_ids=["REG-NEW"], decision="step 2 supersession")

    monkeypatch.setattr("app.rules.registry.precedence.pick_active_rule", fake_pick)
    rule, resolution = registry.active_rule("min_attendance_pct", AS_OF, "B.Tech CSE", 2023)
    assert rule.rule_id == "ATT-MIN-02"
    assert resolution.decision == "step 2 supersession"
    assert captured["sources"]["REG-NEW"].doc_id == "REG-NEW"


def test_rule_registry_passes_future_rule_to_precedence(tiny_db, monkeypatch):
    from app.policy import source_register
    from app.rules import registry
    from app.schemas import Resolution

    source_register.upsert_source(
        SourceMetadata(
            doc_id="REG-FUTURE", title="Future", issuer="Dean", authority_level=2,
            doc_type="circular", version="1", effective_from=date(2026, 11, 1),
        )
    )
    registry.add_rule(Rule(
        rule_id="ATT-MIN-03", description="Future attendance", parameter="min_attendance_pct",
        operator=">=", value="85", effective_from=date(2026, 11, 1), source_doc_id="REG-FUTURE",
        source_section="Clause 7.2, p. 4",
    ))

    def fake_pick(rules, sources, as_of, programme=None, batch=None):
        assert rules[0].effective_from == date(2026, 11, 1)
        return None, Resolution(upcoming_doc_ids=["REG-FUTURE"])

    monkeypatch.setattr("app.rules.registry.precedence.pick_active_rule", fake_pick)
    rule, resolution = registry.active_rule("min_attendance_pct", AS_OF, "B.Tech CSE", 2023)
    assert rule is None
    assert resolution.upcoming_doc_ids == ["REG-FUTURE"]


def test_seed_rules_rejects_unknown_source(tiny_db, tmp_path):
    from scripts.seed_rules import seed_rules

    csv_path = tmp_path / "rules.csv"
    csv_path.write_text(
        "rule_id,description,parameter,operator,value,scope_programmes,scope_batches,effective_from,"
        "effective_to,source_doc_id,source_section\n"
        "ATT-MIN-99,Attendance,min_attendance_pct,>=,75,ALL,ALL,2026-01-01,,MISSING,7.2\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown source"):
        seed_rules(csv_path)


def test_rule_extractor_stores_only_literal_candidate(tiny_db, monkeypatch):
    from types import SimpleNamespace

    from app.rules import extractor
    from app.schemas import Chunk

    meta = SourceMetadata(
        doc_id="CIRC-2026-10", title="Attendance Circular", issuer="Dean",
        authority_level=2, doc_type="circular", version="1",
        effective_from=date(2026, 10, 1), scope_programmes="B.Tech CSE", scope_batches="2023",
    )
    chunk = Chunk(
        chunk_id="CIRC-2026-10::0", doc_id=meta.doc_id,
        text="Clause 7.2: Minimum attendance is 75% for examination eligibility.",
        section="7.2", page=2, meta=meta,
    )
    monkeypatch.setattr(extractor, "get_settings", lambda: SimpleNamespace(mock_llm=False))

    def fake_complete_json(system, user, schema, usage=None):
        return schema.model_validate({
            "rules": [
                {
                    "parameter": "min_attendance_pct", "description": "Minimum attendance",
                    "operator": ">=", "value": "75",
                    "quote": "Minimum attendance is 75% for examination eligibility.",
                },
                {
                    "parameter": "min_attendance_pct", "description": "Hallucinated rule",
                    "operator": ">=", "value": "90",
                    "quote": "Minimum attendance is 90% for examination eligibility.",
                },
            ]
        })

    monkeypatch.setattr(extractor.llm, "complete_json", fake_complete_json)
    rules = extractor.extract_rules(meta, [chunk])

    assert [rule.value for rule in rules] == ["75"]
    with db.connect() as conn:
        stored = conn.execute(
            "SELECT value, source_section FROM rule_registry WHERE source_doc_id = ?",
            (meta.doc_id,),
        ).fetchall()
    assert [tuple(row) for row in stored] == [("75", "7.2 (page 2)")]
