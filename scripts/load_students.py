"""Load judge/test students from CSVs in the Annex C schema. Owner: Yuvraj (F7).

Usage:  python scripts/load_students.py --dir test_students/

Expected files (any subset, loaded in this order so foreign keys hold):
  students.csv, courses.csv, attendance.csv, results.csv, rule_registry.csv (optional)
Judges use this live: it must accept their IDs (S9000-S9999, courses starting JDG), report
exactly what it loaded and what it rejected, and never crash on one bad row.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db
from scripts import validate_students

LOAD_ORDER = ("students", "courses", "attendance", "results", "rule_registry")


def load_directory(directory: Path) -> dict:
    """Load CSV tables in foreign-key order and report row-level failures."""
    db.init_db()
    loaded = {table: 0 for table in LOAD_ORDER}
    rejected: list[dict] = []

    for table in LOAD_ORDER:
        path = directory / f"{table}.csv"
        if not path.exists():
            continue
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except Exception as exc:  # noqa: BLE001 - a bad file must not abort other tables
            rejected.append({"table": table, "row": {}, "reason": f"could not read CSV: {exc}"})
            continue

        try:
            valid_rows, violations = validate_students.validate_rows(table, rows)
        except NotImplementedError:
            valid_rows, violations = rows, []
        except Exception as exc:  # noqa: BLE001 - validator failures are row-safe at load boundary
            valid_rows, violations = [], [{"row": {}, "reason": f"validation failed: {exc}"}]

        for violation in violations:
            rejected.append({
                "table": table,
                "row": violation.get("row", {}),
                "reason": violation.get("reason", "validation failed"),
            })
        for row in valid_rows:
            try:
                loaded[table] += db.upsert_rows(table, [row])
            except Exception as exc:  # noqa: BLE001 - SQLite constraints become row rejections
                rejected.append({"table": table, "row": row, "reason": str(exc)})

    return {"loaded": loaded, "rejected": rejected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path, help="folder with Annex C CSV files")
    args = parser.parse_args()
    print(json.dumps(load_directory(args.dir), indent=2))


if __name__ == "__main__":
    main()
