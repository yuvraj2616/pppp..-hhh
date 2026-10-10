"""Synthetic student data generator. Owner: Yuvraj (F8).

Deliverable (Section 4.2): the exact prompts (verbatim, in data/synthetic/prompts/), the model
that produced the data, this generator, the validator and its output, and a data card.

Design:
  - Pydantic models mirror Annex C rows; the LLM is called in JSON mode with the model's JSON
    schema, output validated, invalid rows retried (max 2) with the error message appended.
  - The LLM generates realistic variety (names, course mixes, marks spread). Edge cases are
    NOT left to chance: they are injected deterministically and listed with their student IDs.
  - Minimums: >= 30 students, 2 programmes, 2 batches, 6 courses.
  - Never use S9000-S9999 or course codes starting JDG (reserved for judges).
  - Write CSVs to data/synthetic/ and generation_log.json (model, temperature, calls, seed, timestamps).

Edge cases to inject (see the guide): attendance exactly at the threshold; one class below it;
marks just below the pass mark; an ABSENT result; a DETAINED student; multiple backlogs;
CGPA exactly at the placement cut-off.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.llm import client as llm

PROMPTS_DIR = Path("data/synthetic/prompts")
OUT_DIR = Path("data/synthetic")
PASS_MARKS_PCT = 50
ATTENDANCE_PCT = 75
PLACEMENT_CGPA = 6.0


class StudentRow(BaseModel):
    """Annex C student row."""

    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(pattern=r"^S[0-9]{4}$")
    full_name: str
    programme: str
    batch_year: int
    current_semester: int
    cgpa: float
    active_backlogs: int


class CourseRow(BaseModel):
    """Annex C course row."""

    model_config = ConfigDict(extra="forbid")
    course_code: str
    course_name: str
    programme: str
    semester: int
    credits: int


class AttendanceRow(BaseModel):
    """Annex C attendance row."""

    model_config = ConfigDict(extra="forbid")
    student_id: str
    course_code: str
    classes_held: int
    classes_attended: int


class ResultRow(BaseModel):
    """Annex C result row."""

    model_config = ConfigDict(extra="forbid")
    student_id: str
    course_code: str
    exam_session: str
    exam_type: str
    internal_marks: int | None = None
    external_marks: int | None = None
    total_marks: int | None = None
    max_marks: int
    result: str


class GeneratedBatch(BaseModel):
    """Structured LLM output for one generation batch."""

    students: list[StudentRow]
    courses: list[CourseRow]
    attendance: list[AttendanceRow]
    results: list[ResultRow]


def _mock_data(count: int, seed: int) -> GeneratedBatch:
    """Create deterministic synthetic base data for offline generation."""
    randomizer = random.Random(seed)
    programmes = [("B.Tech CSE", "CS"), ("BBA", "BA")]
    courses = [
        CourseRow(course_code=f"{prefix}{index:03d}", course_name=f"{programme} Course {index}", programme=programme,
                  semester=(index % 4) + 1, credits=4)
        for programme, prefix in programmes for index in range(1, 4)
    ]
    students: list[StudentRow] = []
    attendance: list[AttendanceRow] = []
    results: list[ResultRow] = []
    for index in range(count):
        programme, _ = programmes[index % 2]
        student_id = f"S{1001 + index:04d}"
        course = courses[(index % 2) * 3 + ((index // 2) % 3)]
        students.append(StudentRow(
            student_id=student_id, full_name=f"Synthetic Student {index + 1}", programme=programme,
            batch_year=2023 + (index % 2), current_semester=(index % 6) + 1,
            cgpa=round(6.2 + randomizer.random() * 3.2, 2), active_backlogs=0,
        ))
        total = randomizer.randint(55, 95)
        attendance.append(AttendanceRow(student_id=student_id, course_code=course.course_code,
                                        classes_held=40, classes_attended=randomizer.randint(30, 40)))
        results.append(ResultRow(
            student_id=student_id, course_code=course.course_code, exam_session="2026-10", exam_type="REGULAR",
            internal_marks=total // 2, external_marks=total - total // 2, total_marks=total, max_marks=100,
            result="PASS" if total >= PASS_MARKS_PCT else "FAIL",
        ))
    return GeneratedBatch(students=students, courses=courses, attendance=attendance, results=results)


def _validate_batch(batch: GeneratedBatch) -> None:
    """Reject duplicate keys and broken student/course references."""
    student_map = {student.student_id: student for student in batch.students}
    course_map = {course.course_code: course for course in batch.courses}
    if len(student_map) != len(batch.students) or len(course_map) != len(batch.courses):
        raise ValueError("duplicate student or course key")
    for row in [*batch.attendance, *batch.results]:
        if row.student_id not in student_map or row.course_code not in course_map:
            raise ValueError(f"unknown foreign key in {row.model_dump()}")
        if student_map[row.student_id].programme != course_map[row.course_code].programme:
            raise ValueError(f"programme mismatch for {row.student_id}/{row.course_code}")


def _ollama_batch(prompt: str, usage: dict[str, int]) -> GeneratedBatch:
    """Request one structured batch through the client, with direct Ollama fallback."""
    usage["calls"] += 1
    try:
        return llm.complete_json(system="Generate strict synthetic Annex C JSON.", user=prompt, schema=GeneratedBatch)
    except Exception as client_error:  # noqa: BLE001 - direct HTTP is the documented fallback
        import httpx

        response = httpx.post(
            f"{get_settings().ollama_base_url}/api/chat",
            json={"model": get_settings().llm_model, "stream": False, "format": GeneratedBatch.model_json_schema(),
                  "messages": [{"role": "system", "content": "Generate synthetic Annex C JSON only."},
                               {"role": "user", "content": f"{prompt}\nPrevious error: {client_error}"}]},
            timeout=get_settings().llm_timeout_s,
        )
        response.raise_for_status()
        return GeneratedBatch.model_validate_json(response.json()["message"]["content"])


def _generate_base(count: int, seed: int, batch_size: int, usage: dict[str, int]) -> GeneratedBatch:
    """Generate and validate base rows in small batches with two retries."""
    if get_settings().mock_llm:
        return _mock_data(count, seed)
    batches: list[GeneratedBatch] = []
    for start in range(0, count, batch_size):
        expected = min(batch_size, count - start)
        prompt = (f"Generate exactly {expected} students, at least six shared courses across two programmes, "
                  "valid foreign keys, and no S9000-S9999 or JDG* codes.")
        error = ""
        for attempt in range(3):
            try:
                batch = _ollama_batch(f"{prompt}\n{error}", usage)
                _validate_batch(batch)
                batches.append(batch)
                break
            except (ValidationError, ValueError, KeyError) as exc:
                error = f"Validation error on attempt {attempt + 1}: {exc}"
        else:
            raise RuntimeError(f"could not generate a valid batch after 3 attempts: {error}")
    return GeneratedBatch(
        students=[row for batch in batches for row in batch.students],
        courses=list({row.course_code: row for batch in batches for row in batch.courses}.values()),
        attendance=[row for batch in batches for row in batch.attendance],
        results=[row for batch in batches for row in batch.results],
    )


def _inject_edges(data: GeneratedBatch) -> dict[str, str]:
    """Inject deterministic policy edge cases and return their student IDs."""
    names = ("attendance_exact_threshold", "attendance_one_class_below", "marks_just_below_pass",
             "absent_result", "detained_student", "multiple_backlogs", "cgpa_at_placement_cutoff")
    edge_ids = {name: data.students[index].student_id for index, name in enumerate(names)}
    attendance = {row.student_id: row for row in data.attendance}
    results = {row.student_id: row for row in data.results if row.exam_type == "REGULAR"}
    student_map = {student.student_id: student for student in data.students}
    courses_by_programme = {course.programme: course for course in data.courses}
    edge_course = {
        student_id: courses_by_programme[student_map[student_id].programme].course_code
        for student_id in edge_ids.values()
    }
    attendance[edge_ids["attendance_exact_threshold"]] = AttendanceRow(
        student_id=edge_ids["attendance_exact_threshold"], course_code=edge_course[edge_ids["attendance_exact_threshold"]],
        classes_held=40, classes_attended=30)
    attendance[edge_ids["attendance_one_class_below"]] = AttendanceRow(
        student_id=edge_ids["attendance_one_class_below"], course_code=edge_course[edge_ids["attendance_one_class_below"]],
        classes_held=40, classes_attended=29)
    results[edge_ids["marks_just_below_pass"]] = ResultRow(
        student_id=edge_ids["marks_just_below_pass"], course_code=edge_course[edge_ids["marks_just_below_pass"]],
        exam_session="2026-10", exam_type="REGULAR",
        internal_marks=24, external_marks=25, total_marks=49, max_marks=100, result="FAIL")
    results[edge_ids["absent_result"]] = ResultRow(
        student_id=edge_ids["absent_result"], course_code=edge_course[edge_ids["absent_result"]],
        exam_session="2026-10", exam_type="REGULAR",
        max_marks=100, result="ABSENT")
    results[edge_ids["detained_student"]] = ResultRow(
        student_id=edge_ids["detained_student"], course_code=edge_course[edge_ids["detained_student"]],
        exam_session="2026-10", exam_type="REGULAR",
        internal_marks=10, external_marks=10, total_marks=20, max_marks=100, result="DETAINED")
    student_map[edge_ids["multiple_backlogs"]].active_backlogs = 3
    student_map[edge_ids["marks_just_below_pass"]].active_backlogs = 1
    student_map[edge_ids["cgpa_at_placement_cutoff"]].cgpa = PLACEMENT_CGPA
    data.students = list(student_map.values())
    data.attendance = list(attendance.values())
    multiple_id = edge_ids["multiple_backlogs"]
    data.results = [row for row in results.values() if row.student_id != multiple_id]
    multiple_programme = student_map[multiple_id].programme
    multiple_courses = [course for course in data.courses if course.programme == multiple_programme][:3]
    data.results.extend(
        ResultRow(student_id=multiple_id, course_code=course.course_code, exam_session=f"2026-{index + 10:02d}",
                  exam_type="REGULAR", internal_marks=24, external_marks=25, total_marks=49, max_marks=100,
                  result="FAIL")
        for index, course in enumerate(multiple_courses)
    )
    return edge_ids


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write model dictionaries to a CSV file."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate(students: int, seed: int, out: Path, batch_size: int = 12) -> dict[str, Any]:
    """Generate synthetic Annex C CSVs, edge cases, and a reproducibility log."""
    if students < 30:
        raise ValueError("students must be at least 30")
    out.mkdir(parents=True, exist_ok=True)
    usage = {"calls": 0}
    data = _generate_base(students, seed, batch_size, usage)
    edge_cases = _inject_edges(data)
    _write_csv(out / "students.csv", [row.model_dump(mode="json") for row in data.students])
    _write_csv(out / "courses.csv", [row.model_dump(mode="json") for row in data.courses])
    _write_csv(out / "attendance.csv", [row.model_dump(mode="json") for row in data.attendance])
    _write_csv(out / "results.csv", [row.model_dump(mode="json", exclude_none=True) for row in data.results])
    _write_csv(out / "rule_registry.csv", [
        {"rule_id": "ATT-MIN-SYN", "description": "Synthetic minimum attendance", "parameter": "min_attendance_pct",
         "operator": ">=", "value": str(ATTENDANCE_PCT), "scope_programmes": "ALL", "scope_batches": "ALL",
         "effective_from": "2024-07-01", "effective_to": "", "source_doc_id": "SYNTHETIC-RULES", "source_section": "1"},
        {"rule_id": "PASS-MIN-SYN", "description": "Synthetic pass percentage", "parameter": "pass_marks_pct",
         "operator": ">=", "value": str(PASS_MARKS_PCT), "scope_programmes": "ALL", "scope_batches": "ALL",
         "effective_from": "2024-07-01", "effective_to": "", "source_doc_id": "SYNTHETIC-RULES", "source_section": "2"},
        {"rule_id": "PLC-CGPA-SYN", "description": "Synthetic placement CGPA", "parameter": "min_cgpa_placement",
         "operator": ">=", "value": str(PLACEMENT_CGPA), "scope_programmes": "ALL", "scope_batches": "ALL",
         "effective_from": "2024-07-01", "effective_to": "", "source_doc_id": "SYNTHETIC-RULES", "source_section": "3"},
        {"rule_id": "PLC-BACK-SYN", "description": "Synthetic placement backlogs", "parameter": "max_backlogs_placement",
         "operator": "<=", "value": "0", "scope_programmes": "ALL", "scope_batches": "ALL",
         "effective_from": "2024-07-01", "effective_to": "", "source_doc_id": "SYNTHETIC-RULES", "source_section": "4"},
    ])
    log = {"model": get_settings().model_label, "temperature": 0.0 if get_settings().mock_llm else 0.2,
           "calls": usage["calls"], "seed": seed, "students": students,
           "generated_at": datetime.now(timezone.utc).isoformat(), "edge_cases": edge_cases}
    (out / "generation_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    return log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--students", type=int, default=36)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    print(json.dumps(generate(args.students, args.seed, args.out), indent=2))


if __name__ == "__main__":
    main()
