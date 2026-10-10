"""Deterministic eligibility tools (R5, R6). Owner: Hritik (F12).

Each check returns output {'result': ELIGIBLE | NOT_ELIGIBLE | UNKNOWN, 'rule_id', 'threshold',
'actual', 'reason', 'assumptions': [...]} plus an AppliedRule list, and the thresholds come
from registry.active_rule(...), never from constants. UNKNOWN when no rule applies.

What-if (R6): overrides let the workflow ask "if I pass the supplementary" without touching
the database, e.g. check_placement_eligibility(sid, as_of, overrides={'active_backlogs': 0}).
Every override must be echoed in 'assumptions'.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.rules import registry
from app.schemas import AppliedRule, ToolCall
from app.tools import student

CheckResult = tuple[dict[str, Any], ToolCall, list[AppliedRule]]


def compare(actual: float, operator: str, value: str) -> bool:
    """Compare a value using a rule registry operator."""
    if operator == "in":
        return str(actual).casefold() in {item.strip().casefold() for item in value.split(";")}

    if operator == "between":
        parts = [part.strip() for part in value.split(";")]
        if len(parts) != 2:
            raise ValueError("between requires two semicolon-separated values")
        lower, upper = (float(part) for part in parts)
        return lower <= float(actual) <= upper

    if operator not in {">=", "<=", ">", "<", "=="}:
        raise ValueError(f"unknown operator: {operator}")
    actual_number = float(actual)
    expected = float(value)
    if operator == ">=":
        return actual_number >= expected
    if operator == "<=":
        return actual_number <= expected
    if operator == ">":
        return actual_number > expected
    if operator == "<":
        return actual_number < expected
    return actual_number == expected


def check_exam_eligibility(student_id: str, course_code: str, as_of: date) -> CheckResult:
    """Check exam eligibility from the student's attendance and active rule."""
    profile, _ = student.get_student_profile(student_id)
    attendance, _ = student.get_attendance(student_id, course_code)
    rule, _ = registry.active_rule("min_attendance_pct", as_of, profile["programme"], profile["batch_year"])
    actual = attendance["attendance_pct"]
    if rule is None:
        return _result(
            "check_exam_eligibility", {"student_id": student_id, "course_code": course_code},
            {"result": "UNKNOWN", "rule_id": None, "threshold": None, "actual": actual,
             "reason": "No applicable attendance rule was found.", "assumptions": []}, [],
        )

    eligible = compare(actual, rule.operator, rule.value)
    output = {
        "result": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "rule_id": rule.rule_id,
        "threshold": rule.value,
        "actual": actual,
        "reason": _reason("Attendance", actual, rule.operator, rule.value, eligible),
        "assumptions": [],
    }
    return _result(
        "check_exam_eligibility", {"student_id": student_id, "course_code": course_code}, output,
        [_applied(rule)],
    )


def check_supplementary_eligibility(student_id: str, course_code: str, as_of: date) -> CheckResult:
    """Check supplementary eligibility from the latest regular result and active rule."""
    profile, _ = student.get_student_profile(student_id)
    results, _ = student.get_results(student_id, course_code)
    regular = next((item for item in results["results"] if item["exam_type"] == "REGULAR"), None)
    rule, _ = registry.active_rule("supp_eligible_results", as_of, profile["programme"], profile["batch_year"])
    actual = regular["result"] if regular else None
    if rule is None or actual is None:
        return _result(
            "check_supplementary_eligibility", {"student_id": student_id, "course_code": course_code},
            {"result": "UNKNOWN", "rule_id": None, "threshold": None, "actual": actual,
             "reason": "No applicable supplementary rule or regular result was found.", "assumptions": []},
            [_applied(rule)] if rule else [],
        )

    eligible = compare(actual, rule.operator, rule.value)
    output = {
        "result": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "rule_id": rule.rule_id,
        "threshold": rule.value,
        "actual": actual,
        "reason": _reason("The regular result", actual, rule.operator, rule.value, eligible),
        "assumptions": [],
    }
    return _result(
        "check_supplementary_eligibility", {"student_id": student_id, "course_code": course_code}, output,
        [_applied(rule)],
    )


def check_placement_eligibility(
    student_id: str, as_of: date, overrides: dict[str, Any] | None = None
) -> CheckResult:
    """Check placement eligibility using CGPA and backlog rules, with non-persistent overrides."""
    profile, _ = student.get_student_profile(student_id)
    assumptions = [f"{key}={value}" for key, value in (overrides or {}).items()]
    values = {"cgpa": profile["cgpa"], "active_backlogs": profile["active_backlogs"]}
    for key in values:
        if overrides and key in overrides:
            values[key] = overrides[key]

    cgpa_rule, _ = registry.active_rule("min_cgpa_placement", as_of, profile["programme"], profile["batch_year"])
    backlog_rule, _ = registry.active_rule("max_backlogs_placement", as_of, profile["programme"], profile["batch_year"])
    rules = [rule for rule in (cgpa_rule, backlog_rule) if rule is not None]
    applied = [_applied(rule) for rule in rules]
    if cgpa_rule is None or backlog_rule is None:
        output = {
            "result": "UNKNOWN", "rule_id": [rule.rule_id for rule in rules],
            "threshold": {"cgpa": cgpa_rule.value if cgpa_rule else None,
                           "active_backlogs": backlog_rule.value if backlog_rule else None},
            "actual": values, "reason": "No applicable placement rule was found for every required criterion.",
            "assumptions": assumptions,
        }
        return _result("check_placement_eligibility", {"student_id": student_id, "overrides": overrides or {}}, output, applied)

    cgpa_ok = compare(values["cgpa"], cgpa_rule.operator, cgpa_rule.value)
    backlog_ok = compare(values["active_backlogs"], backlog_rule.operator, backlog_rule.value)
    eligible = cgpa_ok and backlog_ok
    output = {
        "result": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
        "rule_id": [cgpa_rule.rule_id, backlog_rule.rule_id],
        "threshold": {"cgpa": cgpa_rule.value, "active_backlogs": backlog_rule.value},
        "actual": values,
        "reason": "CGPA and active backlogs meet the placement criteria." if eligible
        else "CGPA or active backlogs do not meet the placement criteria.",
        "assumptions": assumptions,
    }
    return _result("check_placement_eligibility", {"student_id": student_id, "overrides": overrides or {}}, output, applied)


def _applied(rule: Any) -> AppliedRule:
    """Convert a registry rule to the public applied-rule audit shape."""
    return AppliedRule(rule_id=rule.rule_id, value=rule.value, source_doc_id=rule.source_doc_id)


def _result(tool: str, inputs: dict[str, Any], output: dict[str, Any], rules: list[AppliedRule]) -> CheckResult:
    """Build a deterministic tool result and matching tool-call record."""
    return output, ToolCall(tool=tool, input=inputs, output=output), rules


def _reason(label: str, actual: Any, operator: str, threshold: str, eligible: bool) -> str:
    """Build a one-sentence explanation without adding policy values."""
    relation = "meets" if eligible else "does not meet"
    return f"{label} {actual} {relation} the rule {operator} {threshold}."
