# Changelog

Append-only. Never rewrite or delete past entries. Newest entries at the bottom.

---

## 2026-08-13 09:00 — Project initialized, docs reviewed, git repo created

- Read `CLAUDE.md` and all three files in `docs/` (`approach.md`, `literature_survey.md`, `technical_architecture.md`) in full before any code.
- Initialized git repository at project root.
- Created this file (`CHANGELOG.md`) and `ARCHITECTURE.md`, seeded from the dated architectural decisions already present in `docs/technical_architecture.md` §0 and inline `[REVISED — ...]` markers.

## 2026-08-13 09:15 — Phase 0: NCERT Class 5 syllabus audit, first-slice topic confirmed

- Audited all 14 chapters of the NCERT Class 5 Math-Magic textbook against two axes: how cleanly the topic decomposes into a checkable step-DAG, and how well its misconceptions are documented in `docs/literature_survey.md` thread B.
- Findings: Chapter 1 ("The Fish Tale," large numbers / multi-digit +−×÷) is the strongest candidate — multi-digit subtraction with borrowing has the deepest misconception grounding in the entire survey (Brown & Burton's DEBUGGY, VanLehn's repair theory, B1–B3) and decomposes into a clean, unambiguous step-DAG. Runners-up: Chapter 13 (long division — richest step-DAG in the syllabus) and Chapter 6 (LCM/HCF — explicitly named clean in `docs/approach.md`). Chapters flagged as poor fits for step-verification in v1: Shapes and Angles, How Many Squares?, Does it Look the Same?, Can You See the Pattern?, Mapping Your Way, Boxes and Sketches, Smart Charts (Data Handling) — these are recognition/visual/interpretive tasks, not linear checkable procedures.
- Presented the audit to Arnav; he confirmed **Chapter 1, multi-digit subtraction with borrowing (large numbers)** as the first verifier/misconception-bank slice.
- Flagged a stale line in `docs/technical_architecture.md` §8 ("LLM access: Claude via API") — superseded by the explicit instruction to use Groq. Recorded as a superseded decision in `ARCHITECTURE.md` rather than silently edited in the source doc.

## 2026-08-13 10:00 — Phase-by-phase build plan approved; Phase 1 begins

- Wrote a detailed phase-by-phase plan (Phase 1: schema+verifier+misconception bank; Phase 2: error classification; Phase 3: dialogue orchestrator; Phase 4: frontend — the confirmed "working prototype" checkpoint) and got it approved. Working autonomously through phase boundaries until Phase 4 completes, per explicit instruction, with the existing mid-phase-ambiguity and architecture-revision pause conditions still in force.
- Phase 1 repo scaffold: `backend/` (Python/FastAPI package under `src/studyhelp/`, `pyproject.toml` with ruff+mypy config, `.env.example` documenting every config var per twelve-factor), `frontend/` placeholder, `docker-compose.yml` (api + postgres + redis), `backend/Dockerfile`, `.github/workflows/ci.yml` with a `lint` job (ruff check, ruff format --check, mypy strict). Package structure includes empty `classification/` and `dialogue/` stub packages (filled in Phases 2–3) so those phases won't need a restructure.
- Verified locally: `pip install -e ".[dev]"` succeeds in a fresh venv; `ruff check`, `ruff format --check`, and `mypy --strict` all pass clean on the initial scaffold.

## 2026-08-13 10:30 — Phase 1: domain step-schema + verifier-boundary pydantic schemas

- `schemas/step_schema.py`: topic-agnostic `Problem`/`StepNode`/`AltPath`/`NcertRef` domain models. `expected_state` stays an untyped dict at this layer deliberately — per-step-type typed field models belong next to the topic's checkers, not in the shared schema, so a future topic doesn't have to fight this file's types.
- `schemas/verify.py`: pipeline-boundary types — `StudentStep` (structured `fields` dict, never a raw string), `ProblemState`, `ErrorSignal`/`FieldDiscrepancy` (deliberately descriptive not diagnostic — misconception classification is Phase 2), `VerifyResult`.
- Added the canonical worked-example fixture `seed/fixtures/problems/ch1_subtraction_borrowing/problem_014_542_187.json` — a full 9-node step-DAG for 542−187 (double cascading borrow), including a non-adjacent alt-path node that demonstrates the DAG-not-list requirement (D11) by rejoining the main path after a combined borrow+subtract action.
- 16 serialization/round-trip tests in `tests/unit/schemas/`, all passing; ruff+mypy clean.
- CI: added a `test` job (unit tests, no DB needed yet — these schemas are pure). Postgres-backed integration/golden jobs come once those pieces exist.
