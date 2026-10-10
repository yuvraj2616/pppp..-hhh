"""Seed the rule registry from data/rules_seed.csv. Owner: Hritik (F10).

Every row must point at a real clause: source_doc_id exists in the Source Register and
source_section is the clause/page that states the threshold. Judges open that page to check.

Usage:  python scripts/seed_rules.py [--csv data/rules_seed.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db
from app.rules import registry
from app.schemas import Rule


def seed_rules(path: Path) -> int:
    """Validate and insert all rules from a CSV, returning the number inserted."""
    db.init_db()
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    rules: list[Rule] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            rule = Rule.model_validate(row)
        except Exception as exc:  # noqa: BLE001 - report the offending seed row
            raise ValueError(f"invalid rule row {row_number}: {exc}") from exc
        if registry.source_register.get_source(rule.source_doc_id) is None:
            raise ValueError(f"rule row {row_number} references unknown source: {rule.source_doc_id}")
        rules.append(rule)

    for rule in rules:
        registry.add_rule(rule)
    return len(rules)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path("data/rules_seed.csv"))
    args = parser.parse_args()
    print(f"seeded {seed_rules(args.csv)} rules")


if __name__ == "__main__":
    main()
