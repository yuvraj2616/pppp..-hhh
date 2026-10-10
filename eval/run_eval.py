"""Evaluation runner (R12, Section 7). Owner: Pratham (F19).

Usage:
  python eval/run_eval.py --config baseline                      # in-process, uses current env
  EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2 python eval/run_eval.py --config minilm
  CHUNK_STRATEGY=fixed python eval/run_eval.py --config fixed-chunks
  python eval/run_eval.py --compare baseline minilm fixed-chunks  # writes the comparison table

Each run writes eval/results/<config>.json; --compare writes the table into eval/report.md.

Metrics (state the method in the report - exact match for numbers/dates and answer_type,
human-graded rubric for wording):
  answer_correctness       expected_answer_type matches AND expected_value appears in the answer
  citation_accuracy        every expected source (doc_id#section) is among the citations, and cited
                           sections actually contain the claim (spot-check by hand, record how many)
  abstention_accuracy      unanswerable -> not_found; answerable -> not not_found
  tool_result_correctness  expected_tools were invoked and their output matches expected_value
  retrieval_hit_rate       expected doc_id appears in the audit record's sources_retrieved (top-k)
  latency p50 / p95        from the audit record latency_ms
  cost                     llm_calls and tokens per question from the audit record
Coverage required: >= 20 questions; >= 3 unanswerable; >= 3 versions/conflicts; >= 4 personal via
tools; >= 2 other-student attempts; >= 2 multi-step.
"""

from __future__ import annotations

import argparse
from pathlib import Path

QUESTIONS = Path("eval/questions.jsonl")
RESULTS_DIR = Path("eval/results")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="baseline")
    parser.add_argument("--compare", nargs="*")
    parser.parse_args()
    raise NotImplementedError("F19: eval runner")


if __name__ == "__main__":
    main()
