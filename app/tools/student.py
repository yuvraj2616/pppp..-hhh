"""Student-data tools (R5, R7). Owner: Hritik (F11).

Every tool:
  - takes student_id from the workflow (which got it from the X-Student-Id header only),
  - returns (output_dict, ToolCall) so the workflow can put it in tools_invoked and the audit,
  - computes in Python (attendance % = attended / held * 100, rounded to 2 dp), never via the LLM,
  - raises LookupError for an unknown student/course (the workflow turns it into not_found or
    clarification_needed).
"""

from __future__ import annotations

from typing import Any

from app.data import db
from app.schemas import ToolCall

ToolResult = tuple[dict[str, Any], ToolCall]


def get_student_profile(student_id: str) -> ToolResult:
    """Return the non-identifying academic profile for a student."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT programme, batch_year, current_semester, cgpa, active_backlogs "
            "FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
    if row is None:
        raise LookupError(f"unknown student: {student_id}")

    output = dict(row)
    return output, ToolCall(tool="get_student_profile", input={"student_id": student_id}, output=output)


def find_course(student_id: str, text: str) -> list[dict[str, Any]]:
    """Find programme courses by exact code or case-insensitive partial name."""
    with db.connect() as conn:
        student = conn.execute(
            "SELECT programme FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if student is None:
            raise LookupError(f"unknown student: {student_id}")

        rows = conn.execute(
            "SELECT course_code, course_name, programme, semester, credits "
            "FROM courses "
            "WHERE programme = ? AND "
            "(UPPER(course_code) = UPPER(?) OR LOWER(course_name) LIKE LOWER(?) ESCAPE '\\') "
            "ORDER BY course_code",
            (student["programme"], text, f"%{_escape_like(text)}%"),
        ).fetchall()
    return [dict(row) for row in rows]


def get_attendance(student_id: str, course_code: str) -> ToolResult:
    """Return attendance counts and the percentage computed by Python."""
    with db.connect() as conn:
        _require_student(conn, student_id)
        row = conn.execute(
            "SELECT a.classes_held, a.classes_attended "
            "FROM attendance AS a "
            "JOIN courses AS c ON c.course_code = a.course_code "
            "WHERE a.student_id = ? AND UPPER(a.course_code) = UPPER(?)",
            (student_id, course_code),
        ).fetchone()
    if row is None:
        raise LookupError(f"unknown course or attendance: {course_code}")

    held = row["classes_held"]
    attended = row["classes_attended"]
    output = {
        "classes_held": held,
        "classes_attended": attended,
        "attendance_pct": round(attended / held * 100, 2),
    }
    call = ToolCall(tool="get_attendance", input={"student_id": student_id, "course_code": course_code}, output=output)
    return output, call


def get_results(student_id: str, course_code: str | None = None) -> ToolResult:
    """Return the latest stored result for each requested course and exam type."""
    with db.connect() as conn:
        _require_student(conn, student_id)
        if course_code is not None:
            course = conn.execute(
                "SELECT 1 FROM courses AS c JOIN students AS s ON s.programme = c.programme "
                "WHERE s.student_id = ? AND UPPER(c.course_code) = UPPER(?)",
                (student_id, course_code),
            ).fetchone()
            if course is None:
                raise LookupError(f"unknown course: {course_code}")

        query = (
            "SELECT course_code, exam_session, exam_type, internal_marks, external_marks, "
            "total_marks, max_marks, result "
            "FROM (SELECT r.*, ROW_NUMBER() OVER ("
            "PARTITION BY r.course_code, r.exam_type ORDER BY r.exam_session DESC"
            ") AS row_number FROM results AS r WHERE r.student_id = ?"
        )
        params: list[Any] = [student_id]
        if course_code is not None:
            query += " AND UPPER(r.course_code) = UPPER(?)"
            params.append(course_code)
        query += ") WHERE row_number = 1 ORDER BY course_code, exam_type"
        rows = conn.execute(query, params).fetchall()

    output = {"results": [dict(row) for row in rows]}
    call = ToolCall(
        tool="get_results",
        input={"student_id": student_id, "course_code": course_code},
        output=output,
    )
    return output, call


def _require_student(conn: Any, student_id: str) -> None:
    """Raise `LookupError` unless the student exists."""
    row = conn.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        raise LookupError(f"unknown student: {student_id}")


def _escape_like(value: str) -> str:
    """Escape wildcard characters before placing text in a parameterized LIKE pattern."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
