# Synthetic data card (Annex E)

> Owner: Yuvraj (F9).

## Purpose

This is fabricated demonstration and judge-safe test data for student services. It contains no
real student records.

## Provenance and generation

- Generator: `scripts/generate_students.py`.
- Run metadata: model `mock`, temperature `0.0`, seed `42`, `0` model calls, generated at
  `2026-10-10T11:41:33.917582+00:00`; see `data/synthetic/generation_log.json`.
- Prompts: `data/synthetic/prompts/system.txt` and `data/synthetic/prompts/user.txt`.
- The mock path is deterministic. Non-mock runs request structured Ollama JSON in small batches,
  validate Pydantic rows and foreign keys, and retry invalid batches up to two times with the
  validation error appended.

## Schema and counts

All rows use the Annex C table shapes and are checked with Pydantic models, foreign-key checks,
and the validator in `scripts/validate_students.py`.

| Table | Rows | Distribution |
| --- | ---: | --- |
| `students` | 36 | 18 B.Tech CSE; 18 BBA |
| `courses` | 6 | 3 B.Tech CSE; 3 BBA |
| `attendance` | 36 | 10 distinct percentages from 72.5% to 97.5%; 4 rows at 75.0% |
| `results` | 38 | 32 PASS; 4 FAIL; 1 ABSENT; 1 DETAINED; all REGULAR |
| `rule_registry` | 4 | Synthetic attendance, pass-mark, placement-CGPA, and placement-backlog rules |

### Student programme and batch distribution

| Programme | Batch 2023 | Batch 2024 | Total |
| --- | ---: | ---: | ---: |
| B.Tech CSE | 18 | 0 | 18 |
| BBA | 0 | 18 | 18 |
| Total | 18 | 18 | 36 |

The dataset meets the minimum programme and batch counts, but is intentionally not cross-balanced:
programme and batch are correlated in this generated run.

Other observed distributions are CGPA `6.00–9.37`; active backlogs are 34 students at `0`, one
at `1`, and one at `3`. Attendance percentages are computed from `classes_attended/classes_held`
and include the exact threshold and one-class-below cases.

## Deterministic edge cases

| Edge case | Student ID |
| --- | --- |
| Attendance exactly at threshold | `S1001` |
| Attendance one class below threshold | `S1002` |
| Marks just below pass mark | `S1003` |
| ABSENT result | `S1004` |
| DETAINED student | `S1005` |
| Multiple backlogs | `S1006` |
| CGPA exactly at placement cut-off | `S1007` |

## Validation

`data/synthetic/validation_report.txt` records:

```json
{
  "violations": [],
  "warnings": []
}
```

The validator checks required columns and types, student/course ranges, reserved IDs and course
codes, attendance bounds, result marks and consistency, foreign keys, programme matching, and
the relationship between active backlogs and FAIL results. It exits with status `1` when violations
are present; warnings do not fail the run.

## What the LLM got wrong

Nothing was produced by an LLM in this recorded run: `MOCK_LLM=true`, so there were no model calls,
retries, malformed batches, or model-originated validation violations. During implementation, the
first deterministic edge-case assembly produced two backlog-consistency warnings; those were caused
by local fixture construction rather than an LLM, and the generator was corrected before this final
run. The non-mock retry path is implemented but was not exercised here, so this data card makes no
claim about live Ollama output quality.

## Limitations

Synthetic thresholds are demonstration values, not university policy. Names and academic records
are fabricated, programme/batch combinations are correlated in this run, and the generator does
not model every possible course/result combination.
