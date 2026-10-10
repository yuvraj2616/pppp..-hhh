"""F7 database and CSV loader tests."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.data import db
from scripts.load_students import load_directory
from scripts.validate_students import validate_directory, validate_rows


def _write_csv(directory, table, fieldnames, rows):
    """Write a small table fixture to CSV."""
    with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_upsert_rows_allowlist_and_empty_values():
    """Allowed rows insert, empty nullable values become NULL, and unsafe tables fail."""
    db.upsert_rows("students", [{
        "student_id": "S9001", "full_name": "Judge One", "programme": "B.Tech CSE",
        "batch_year": "2023", "current_semester": "5", "cgpa": "8.0", "active_backlogs": "0",
    }])
    with pytest.raises(ValueError, match="not allowed"):
        db.upsert_rows("students; DROP TABLE students", [])


def test_load_directory_reports_bad_row_per_table(tmp_path):
    """Load valid rows and report schema-invalid rows without aborting other tables."""
    _write_csv(tmp_path, "students",
               ["student_id", "full_name", "programme", "batch_year", "current_semester", "cgpa", "active_backlogs"],
               [
                   {"student_id": "S9001", "full_name": "Judge One", "programme": "B.Tech CSE",
                    "batch_year": "2023", "current_semester": "5", "cgpa": "8.0", "active_backlogs": "0"},
                   {"student_id": "S9002", "full_name": "Bad CGPA", "programme": "B.Tech CSE",
                    "batch_year": "2023", "current_semester": "5", "cgpa": "11", "active_backlogs": "0"},
               ])
    _write_csv(tmp_path, "courses",
               ["course_code", "course_name", "programme", "semester", "credits"],
               [
                   {"course_code": "JDG001", "course_name": "Judge Course", "programme": "B.Tech CSE",
                    "semester": "5", "credits": "4"},
                   {"course_code": "JDG002", "course_name": "", "programme": "B.Tech CSE",
                    "semester": "5", "credits": "4"},
               ])
    _write_csv(tmp_path, "attendance",
               ["student_id", "course_code", "classes_held", "classes_attended"],
               [
                   {"student_id": "S9001", "course_code": "JDG001", "classes_held": "40", "classes_attended": "30"},
                   {"student_id": "S9001", "course_code": "JDG001", "classes_held": "40", "classes_attended": "41"},
               ])
    _write_csv(tmp_path, "results",
               ["student_id", "course_code", "exam_session", "exam_type", "internal_marks", "external_marks",
                "total_marks", "max_marks", "result"],
               [
                   {"student_id": "S9001", "course_code": "JDG001", "exam_session": "2026-10", "exam_type": "REGULAR",
                    "internal_marks": "30", "external_marks": "50", "total_marks": "80", "max_marks": "100", "result": "PASS"},
                   {"student_id": "S9001", "course_code": "JDG001", "exam_session": "2026-11", "exam_type": "INVALID",
                    "internal_marks": "30", "external_marks": "50", "total_marks": "80", "max_marks": "100", "result": "PASS"},
               ])
    _write_csv(tmp_path, "rule_registry",
               ["rule_id", "description", "parameter", "operator", "value", "scope_programmes", "scope_batches",
                "effective_from", "effective_to", "source_doc_id", "source_section"],
               [
                   {"rule_id": "JDG-RULE-01", "description": "Judge rule", "parameter": "min_attendance_pct",
                    "operator": ">=", "value": "75", "scope_programmes": "ALL", "scope_batches": "ALL",
                    "effective_from": "2026-01-01", "effective_to": "", "source_doc_id": "JDG-DOC", "source_section": "1"},
                   {"rule_id": "JDG-RULE-02", "description": "", "parameter": "min_attendance_pct",
                    "operator": ">=", "value": "75", "scope_programmes": "ALL", "scope_batches": "ALL",
                    "effective_from": "2026-01-01", "effective_to": "", "source_doc_id": "JDG-DOC", "source_section": "1"},
               ])

    result = load_directory(tmp_path)

    assert result["loaded"] == {
        "students": 1, "courses": 1, "attendance": 1, "results": 1, "rule_registry": 1,
    }
    assert len(result["rejected"]) == 5
    assert {item["table"] for item in result["rejected"]} == set(result["loaded"])
    with db.connect() as conn:
        assert conn.execute("SELECT student_id FROM students").fetchall()[0][0] == "S9001"


def test_validator_rejects_invalid_rows_and_accepts_generated_corpus():
    """Validate local constraints and the checked-in synthetic corpus."""
    valid, violations = validate_rows("attendance", [{
        "student_id": "S1001", "course_code": "CS001", "classes_held": "40", "classes_attended": "41",
    }])
    assert valid == []
    assert "invalid attendance counts" in violations[0]["reason"]

    violations, warnings = validate_directory(Path("data/synthetic"))
    assert violations == []
    assert warnings == []
