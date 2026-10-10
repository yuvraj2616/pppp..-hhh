# AI-Powered University Student Services Assistant

Answers student academic-service questions from authorised university documents and synthetic
student data, with citations, deterministic tools, Annex A conflict resolution and a full audit trail.
Stack: FastAPI · LangGraph · ChromaDB · SQLite · sentence-transformers · Ollama · Streamlit · Docker.

> Team: start with `team/GIT_COMMANDS.md` (setup + daily git loop) and `team/PROMPTS.md` (your AI prompts).
> Architecture and design decisions: `docs/architecture.md`.

## Run it

```bash
# 1. Local LLM on the host (pull before the event)
ollama serve
ollama pull qwen2.5:7b-instruct

# 2. Configure and start API (:8000) + UI (:8501)
cp .env.example .env
docker compose up --build

# 3. Ingest the corpus listed in data/source_register.csv (once; Chroma persists in ./storage)
docker compose exec api python scripts/ingest_corpus.py
docker compose exec api python scripts/seed_rules.py

# 4. Load students (ours or the judges')
docker compose exec api python scripts/load_students.py --dir data/synthetic
```

Without Docker: `pip install -r requirements.txt`, then `uvicorn app.main:app --reload` and `streamlit run ui/app.py`.
Tests without a model: `pip install -r requirements-ci.txt && MOCK_LLM=true pytest -q`.

## API (Section 6 contract)

```bash
curl -s localhost:8000/health

curl -s -X POST localhost:8000/ask -H 'Content-Type: application/json' -H 'X-Student-Id: S1001' \
  -d '{"question": "Am I eligible for the end-semester exam in CS201?", "as_of_date": "2026-10-06"}'

curl -s -X POST localhost:8000/ingest \
  -F file=@circular.pdf \
  -F 'metadata={"doc_id":"ACAD-2026-09","title":"Attendance circular","issuer":"Dean (Academics)","authority_level":2,"doc_type":"circular","version":"1","effective_from":"2026-09-01","supersedes":"ACAD-REG-2024#7.2","scope_programmes":"ALL","scope_batches":"ALL","provenance":"judge upload","retrieved_on":"2026-10-06","synthetic":"N"}'

curl -s localhost:8000/audit/<trace_id>
curl -s localhost:8000/sources
```

## Configuration
| Variable | Default | Purpose |
| --- | --- | --- |
| `MOCK_LLM` | `false` | Deterministic fake LLM for tests and demo fallback |
| `LLM_PROVIDER` | `ollama` | Cloud fallback only if changed (disclosed in `docs/ai_usage.md`) |
| `LLM_MODEL` | `qwen2.5:7b-instruct` | Ollama model |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `CHUNK_STRATEGY` | `section` | `section` or `fixed` (compared in the eval) |
| `TOP_K` | `6` | Chunks retrieved per question |

## Deliverables checklist (Section 8)
- [ ] Repo tagged `final`, this README complete (assumptions, limitations, edge cases)
- [ ] `docker compose up` starts API, UI and stores
- [ ] `data/source_register.csv` + documents (or links)
- [ ] Rule registry in SQLite, every rule linked to a clause (`data/rules_seed.csv`)
- [ ] Synthetic data kit: prompts, generator, validator + output, `docs/data_card.md`
- [ ] `eval/questions.jsonl` + `eval/report.md`
- [ ] Three audit samples in `docs/audit_samples/` (different answer types)
- [ ] `docs/ai_usage.md`, `docs/contribution.md`

## Assumptions, limitations, known edge cases
- (fill during the day)
