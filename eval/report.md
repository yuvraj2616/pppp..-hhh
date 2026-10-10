# Evaluation report

> Owner: Pratham (F19). Filled from `eval/run_eval.py --compare`.

## Method
- Evaluation set: `eval/questions.jsonl`, N = __ questions (coverage table below).
- Scoring: exact match for answer_type, numbers and dates; human-graded rubric for wording; citation pages opened and checked by hand for __ of __ answers.
- LLM-as-judge: not used / used (prompt in `eval/judge_prompt.md`, checked against __ human labels).

## Coverage
| Category | Required | Ours |
| --- | --- | --- |
| Unanswerable | ≥ 3 | |
| Versions / conflicts | ≥ 3 | |
| Personal via tools | ≥ 4 | |
| Other student's data | ≥ 2 | |
| Multi-step | ≥ 2 | |

## Results by configuration
| Metric | baseline (bge-small, section, k=6) | minilm | fixed chunks |
| --- | --- | --- | --- |
| Answer correctness | | | |
| Citation accuracy | | | |
| Abstention accuracy | | | |
| Tool-result correctness | | | |
| Retrieval hit rate | | | |
| Latency p50 / p95 (ms) | | | |
| LLM calls / tokens per question | | | |

## Decision
We chose __ because __ (numbers above).

## Failures we know about
-
