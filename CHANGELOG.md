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

## 2026-08-13 11:15 — Phase 1: SQLAlchemy models + Alembic migration 0001

- `config.py`: twelve-factor `Settings` (pydantic-settings), reading every var documented in `.env.example`; `LLM_PROVIDER` defaults to `mock` (no Groq key exists yet).
- `db/base.py`: async SQLAlchemy engine/session (`asyncpg`), `Base` declarative class.
- `db/models/`: `StepType`, `ProblemModel`, `MisconceptionBankEntry` (+ `ReviewStatus` enum), `BuggyRuleEntry`, `User` (+ `UserRole`), `SessionModel` (+ `ExperimentCondition` enum — persisted per session from commit one, per `CLAUDE.md`'s explicit "don't retrofit the RCT's condition tracking" instruction), `Event` (append-only, composite indexes on `(session_id, created_at)` and `(problem_id, event_type)`). `misconception_bank`/`buggy_rule_library` both carry a composite FK to `step_types(topic, step_type_key)`, keeping the "step type is a first-class, consistently-keyed field" principle (ARCHITECTURE.md D1) enforced at the DB level, not just convention.
- `alembic/env.py`: async-aware (uses `run_sync` for online migrations), with an offline-mode path (`context.is_offline_mode()`) that emits SQL without needing a live DB connection.
- `alembic/versions/0001_initial_schema.py`: hand-written (not autogenerated, since autogenerate needs a live DB to diff against) — creates all seven tables plus three Postgres enum types (`review_status`, `user_role`, `experiment_condition`), in FK-dependency order; `downgrade()` reverses cleanly including enum-type cleanup.
- **Verification note, stated plainly:** this sandboxed dev environment has neither Docker nor a local Postgres install, so `alembic upgrade head` against a *live* database hasn't been exercised here. What was verified: `alembic upgrade head --sql` (offline mode) generates syntactically correct, dependency-ordered Postgres DDL for all seven tables — reviewed in full. `mypy --strict` and `ruff` pass clean on the models. New integration tests (`tests/integration/test_migrations.py`) that round-trip real rows through a real Postgres connection are written and pass their local no-DB path (skip gracefully with a clear reason rather than failing when Postgres isn't reachable — 3/3 skipped locally, confirmed). CI's `test` job now runs a real `postgres:16-alpine` service container, applies the migration for real, and runs these integration tests against it — that's where first live-DB confirmation happens. Flagging this rather than silently claiming full local verification.
- CI: `test` job now spins up a Postgres service container, runs `alembic upgrade head`, then unit + integration tests.

## 2026-08-13 12:00 — Phase 1: verify_step() interface + SubtractionBorrowingVerifier

- `verification/interface.py`: `StepVerifier` Protocol + `VerifierRegistry`. `verification/__init__.py` registers `SubtractionBorrowingVerifier` — adding a topic later means one new module plus one registration line, never touching pipeline code.
- `verification/confidence.py`: named constants `ACCEPT_THRESHOLD=0.9`, `REJECT_THRESHOLD=0.75`, `NON_ADJACENT_MATCH_CONFIDENCE=0.85` (ARCHITECTURE.md D22).
- `verification/topics/subtraction_borrowing/step_checkers.py`: typed per-step-type field models (`CompareColumnFields`/`BorrowFields`/`SubtractColumnFields`/`WriteFinalAnswerFields`) and field-level `compare_to_expected()` producing an agreement ratio.
- `verification/topics/subtraction_borrowing/sympy_utils.py`: the narrow sympy role from D23 — `check_final_identity()` (independent cross-check used when a `write_final_answer` step is accepted) and `check_borrow_arithmetic()`/`check_subtract_arithmetic()` (problem-authoring-time consistency checks, exercised directly in tests).
- `verification/topics/subtraction_borrowing/verifier.py`: `SubtractionBorrowingVerifier.verify_step()` — type-scoped candidate search across the *whole* graph (not just the frontier), exact-match resolution preferring frontier over non-adjacent, and a `max()`-by-agreement near-match resolver implementing the confidence bands from D22 exactly (reject only when agreement ≥ 0.75, otherwise pass through and log).
- 20 new unit tests (31 total in `tests/unit`) directly exercising: full correct walkthrough of the canonical problem, non-adjacent valid match, an exact-boundary reject case (agreement == 0.75 precisely), a genuinely ambiguous passthrough case (D2's false-negative bias as a tested code path, not a comment), unknown-step-type and malformed-input rejection (bias exception — these always reject), and the sympy cross-check utilities in isolation (including a direct test of the B2 bug shape — borrow without decrementing the lender). All passing; ruff+mypy --strict clean.
