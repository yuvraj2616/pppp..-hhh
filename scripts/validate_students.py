"""Validate synthetic or judge data against Annex C. Owner: Yuvraj (F8).

Usage:  python scripts/validate_students.py --dir data/synthetic [--report data/synthetic/validation_report.txt]
Exit code 1 when any violation is found (CI runs this when data/synthetic/students.csv exists).

Checks (Section 4.2 + Annex C):
  - required columns present, types parse, student_id matches S####, cgpa 0-10, semester 1-10, backlogs >= 0
  - attendance: classes_held > 0, 0 <= classes_attended <= classes_held
  - results: total_marks == internal_marks + external_marks; 0 <= total <= max_marks;
             result consistent with marks (PASS >= pass mark, FAIL below it, ABSENT has no marks)
  - foreign keys: every attendance/result row points to an existing student and course;
             course.programme matches a students.programme value
  - active_backlogs consistent with FAIL results (report as a warning if you define it differently)
  - our data must not use reserved IDs S9000-S9999 / JDG* (warning only for judge data)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REQUIRED_COLUMNS = {
    "students": ("student_id", "full_name", "programme", "batch_year", "current_semester", "cgpa", "active_backlogs"),
    "courses": ("course_code", "course_name", "programme", "semester", "credits"),
    "attendance": ("student_id", "course_code", "classes_held", "classes_attended"),
    "results": ("student_id", "course_code", "exam_session", "exam_type", "internal_marks", "external_marks",
                 "total_marks", "max_marks", "result"),
    "rule_registry": ("rule_id", "description", "parameter", "operator", "value", "scope_programmes", "scope_batches",
                       "effective_from", "effective_to", "source_doc_id", "source_section"),
}
PASS_MARKS_PCT = 50


def _number(value: object, field: str) -> float | None:
    """Parse a numeric value, preserving blank nullable fields as None."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not numeric") from exc


def validate_rows(table: str, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate required columns, types, ranges, and row-local Annex C constraints."""
    if table not in REQUIRED_COLUMNS:
        return [], [{"row": {}, "reason": f"unknown table: {table}"}]
    valid: list[dict] = []
    violations: list[dict] = []
    required = set(REQUIRED_COLUMNS[table])
    for row in rows:
        reasons: list[str] = []
        if set(row) != required:
            reasons.append("required columns do not match Annex C")
        try:
            if table == "students":
                if not re.fullmatch(r"S\d{4}", str(row.get("student_id", ""))):
                    reasons.append("student_id must match S####")
                if str(row.get("student_id", "")).startswith("S9"):
                    reasons.append("reserved judge student_id")
                batch_year = int(row["batch_year"])
                semester = int(row["current_semester"])
                cgpa = _number(row["cgpa"], "cgpa")
                backlogs = int(row["active_backlogs"])
                if batch_year < 1900: reasons.append("batch_year is invalid")
                if semester < 1 or semester > 10: reasons.append("current_semester outside 1-10")
                if cgpa is None or cgpa < 0 or cgpa > 10: reasons.append("cgpa outside 0-10")
                if backlogs < 0: reasons.append("active_backlogs must be non-negative")
            elif table == "courses":
                if str(row.get("course_code", "")).upper().startswith("JDG"):
                    reasons.append("reserved judge course_code")
                semester = int(row["semester"])
                int(row["credits"])
                if semester < 1 or semester > 10: reasons.append("semester outside 1-10")
            elif table == "attendance":
                held = int(row["classes_held"])
                attended = int(row["classes_attended"])
                if held <= 0 or attended < 0 or attended > held: reasons.append("invalid attendance counts")
            elif table == "results":
                if row["exam_type"] not in {"REGULAR", "SUPPLEMENTARY"}: reasons.append("invalid exam_type")
                if row["result"] not in {"PASS", "FAIL", "ABSENT", "DETAINED"}: reasons.append("invalid result")
                max_marks = _number(row["max_marks"], "max_marks")
                internal = _number(row["internal_marks"], "internal_marks")
                external = _number(row["external_marks"], "external_marks")
                total = _number(row["total_marks"], "total_marks")
                if max_marks is None or max_marks <= 0: reasons.append("max_marks must be positive")
                if row["result"] == "ABSENT":
                    if any(value is not None for value in (internal, external, total)):
                        reasons.append("ABSENT must have no marks")
                elif None in (internal, external, total):
                    reasons.append("non-ABSENT result requires marks")
                elif total != internal + external:
                    reasons.append("total_marks must equal internal_marks + external_marks")
                elif total < 0 or (max_marks is not None and total > max_marks):
                    reasons.append("total_marks outside range")
                elif row["result"] == "PASS" and total / max_marks * 100 < PASS_MARKS_PCT:
                    reasons.append("PASS is below pass mark")
                elif row["result"] == "FAIL" and total / max_marks * 100 >= PASS_MARKS_PCT:
                    reasons.append("FAIL meets pass mark")
        except (KeyError, TypeError, ValueError) as exc:
            reasons.append(f"invalid field type: {exc}")
        if reasons:
            violations.append({"row": row, "reason": "; ".join(reasons)})
        else:
            valid.append(row)
    return valid, violations


def _read_table(directory: Path, table: str) -> list[dict]:
    """Read one CSV table or return an empty list when absent."""
    path = directory / f"{table}.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_directory(directory: Path) -> tuple[list[dict], list[dict]]:
    """Run row-local and cross-table validation, returning violations and warnings."""
    tables = {table: _read_table(directory, table) for table in REQUIRED_COLUMNS}
    violations: list[dict] = []
    warnings: list[dict] = []
    valid_tables: dict[str, list[dict]] = {}
    for table, rows in tables.items():
        valid, table_violations = validate_rows(table, rows)
        valid_tables[table] = valid
        violations.extend({"table": table, **violation} for violation in table_violations)
    students = {row.get("student_id"): row for row in valid_tables["students"]}
    courses = {row.get("course_code"): row for row in valid_tables["courses"]}
    for table in ("attendance", "results"):
        for row in valid_tables[table]:
            if row.get("student_id") not in students or row.get("course_code") not in courses:
                violations.append({"table": table, "row": row, "reason": "foreign key does not exist"})
            elif students[row["student_id"]]["programme"] != courses[row["course_code"]]["programme"]:
                violations.append({"table": table, "row": row, "reason": "student/course programme mismatch"})
    fail_counts: dict[str, int] = {}
    for row in valid_tables["results"]:
        if row.get("result") == "FAIL":
            fail_counts[row["student_id"]] = fail_counts.get(row["student_id"], 0) + 1
    for student_id, student in students.items():
        if int(student["active_backlogs"]) != fail_counts.get(student_id, 0):
            warnings.append({"table": "students", "row": student, "reason": "active_backlogs differs from FAIL count"})
    return violations, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    violations, warnings = validate_directory(args.dir)
    report = {"directory": str(args.dir), "violations": violations, "warnings": warnings}
    report_path = args.report or args.dir / "validation_report.txt"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
