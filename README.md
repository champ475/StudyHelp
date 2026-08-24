# StudyHelp

A real-time, point-of-error math tutor for Class 5 (NCERT/CBSE) students.

A student solves a problem **step by step**. Each step is checked immediately by a
deterministic symbolic verifier (never the LLM alone) — if it's wrong, the system
diagnoses the specific misconception behind the mistake and guides the student back
with multi-turn Socratic dialogue, the way an attentive parent corrects a child
mid-mistake rather than after the fact. It never hands over the answer directly.

This is both a real product and the basis of a research project — see [`CLAUDE.md`](CLAUDE.md)
for the full architectural brief, [`docs/`](docs/) for the design docs it was built from
(project framing, a 45-paper literature survey, and the primary engineering spec), and
[`ARCHITECTURE.md`](ARCHITECTURE.md) / [`CHANGELOG.md`](CHANGELOG.md) for the dated,
cited record of every architectural decision and change made since.

## Architecture at a glance

- **Backend**: Python, FastAPI, async throughout. Postgres (problems, step-DAGs,
  misconception bank, buggy-rule library, event log) as the durable store; Redis for
  active per-step dialogue-state caching only.
- **Verification**: every submitted step is checked by `sympy` + a per-topic rule
  engine *before* any LLM call — a hard pipeline gate, not a tool the LLM chooses to
  invoke.
- **Error classification**: a buggy-rule library (deterministic, enumerable error
  patterns) is tried first; a closed-set LLM classifier (never open-ended) is the
  fallback, picking only among misconceptions already retrieved for that
  `(topic, step_type)`.
- **Dialogue**: every turn is decide-then-generate — a structured
  `{error_type, remediation_strategy, instructional_intent}` decision first, then a
  child-facing message conditioned on it. Every generated message passes a
  leakage filter and a readability gate before it ever reaches the student.
- **LLM access**: Groq API, behind a provider-agnostic `classify`/`decide`/`generate`
  interface — swapping providers is a config change. Runs against a deterministic
  mock provider until a real API key is supplied, so the full pipeline is testable
  end to end with zero API calls.
- **Frontend**: React + TypeScript, a structured math-aware step-input widget, a
  streaming chat UI for dialogue turns, and per-topic SVG diagrams (shown at
  problem load, and as a deterministic, curated hint during remediation for
  problems where a picture genuinely clarifies the mistake).

## Prerequisites

- [Docker](https://www.docker.com/) + Docker Compose (runs Postgres, Redis, and the API)
- [Node.js](https://nodejs.org/) 18+ (frontend dev server)
- Python 3.11+ (only needed if you want to run the backend outside Docker, or run
  tests/lint locally instead of in a container)

No Groq API key is required to run the app — it defaults to a deterministic mock LLM
provider (`LLM_PROVIDER=mock`) so the full verifier → classifier → dialogue pipeline
works out of the box. Add a real key later (see [Configuration](#configuration)) to
switch on live model calls.

## Quick start (Windows)

```powershell
git clone https://github.com/champ475/StudyHelp.git
cd StudyHelp
./run.ps1
```

`run.ps1` will:
1. Copy `backend/.env.example` → `backend/.env` if it doesn't exist yet.
2. Start Postgres, Redis, and the API via `docker compose up -d --build`.
3. Wait for Postgres's healthcheck, then run pending Alembic migrations inside the API container.
4. Install frontend dependencies on first run (`npm install`, if `frontend/node_modules` is missing).
5. Start the Vite dev server in the foreground.

Then, in a second terminal, seed the database (problems, step-DAGs, misconception
bank, buggy-rule library — safe to re-run, upserts by natural key):

```powershell
docker compose exec api python scripts/seed_db.py
```

Open the app:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000 (health check at `/health`)

`Ctrl+C` stops the frontend dev server. The backend containers keep running — stop
them with `docker compose down` when you're done.

## Quick start (macOS/Linux)

There's no `run.sh` equivalent yet; the same steps done manually:

```bash
git clone https://github.com/champ475/StudyHelp.git
cd StudyHelp
cp backend/.env.example backend/.env

docker compose up -d --build postgres redis api
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_db.py

cd frontend
npm install
npm run dev
```

## Configuration

All config is via environment variables (twelve-factor style) — see
[`backend/.env.example`](backend/.env.example) for the full, documented list. Copy it
to `backend/.env` and edit as needed; `backend/.env` is gitignored and a real key
should never be committed.

Key variables:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local Postgres (docker-compose service) | async SQLAlchemy URL |
| `REDIS_URL` | local Redis (docker-compose service) | dialogue-state cache only, not durable |
| `LLM_PROVIDER` | `mock` | set to `groq` to use real model calls |
| `GROQ_API_KEY` | *(empty)* | required if `LLM_PROVIDER=groq` |
| `GROQ_MODEL` | *(empty)* | required if `LLM_PROVIDER=groq`; must be a model with verified structured-output support |
| `DIALOGUE_TURN_BUDGET` | `4` | max remediation turns before falling back to a worked example |
| `READABILITY_MAX_GRADE` | `5.0` | Flesch-Kincaid grade-level ceiling for generated messages |

## Running tests

**Backend** (from `backend/`, with the venv/dependencies installed — `pip install -e ".[dev]"`,
or run inside the `api` container):

```bash
pytest                 # full suite
ruff check .            # lint
ruff format --check .   # format check
mypy --strict .          # type-check
```

**Frontend** (from `frontend/`):

```bash
npm run typecheck   # tsc --noEmit
npm run lint         # eslint
npm test              # vitest
npm run build         # typecheck + production build
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push.

## Project structure

```
backend/
  src/studyhelp/
    verification/     # per-topic sympy + rule-engine verifiers, one module per topic
    classification/    # buggy-rule matcher + closed-set LLM error classifier
    dialogue/           # orchestrator, decide-then-generate, leakage/readability gates
    llm/                 # provider-agnostic client (mock + Groq), prompts, analogies
    db/                    # SQLAlchemy models, repositories, Alembic migrations
    seed/                    # fixture data: problems, step-DAGs, misconception bank
    api/                       # FastAPI routers
  tests/               # unit + integration tests, mirroring the src/ layout
frontend/
  src/
    components/         # step input, chat UI, diagram panel
    diagrams/            # one SVG renderer per topic
docs/                # project framing, literature survey, engineering spec
CLAUDE.md          # the project brief this codebase was built against
ARCHITECTURE.md    # dated, cited log of every architectural decision
CHANGELOG.md       # dated, append-only log of every meaningful change
```

## Compliance note

This system is designed to handle data from children under 18 in India. India's DPDP
Act 2023 + DPDP Rules 2025 require verifiable parental consent and restrict behavioral
tracking of children's data. **Qualified legal guidance is required before any real
student's data is collected**, including in a small pilot — see `docs/technical_architecture.md`
for sourcing. Nothing in this repository constitutes that guidance.
