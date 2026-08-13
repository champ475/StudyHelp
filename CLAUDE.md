# StudyHelp — Project Brief for Claude Code

You are building **StudyHelp**, a real-time, point-of-error math tutor for Class 5 (NCERT/CBSE) students. Read this file fully before writing any code. Full supporting documents are in `docs/` — read them too before starting implementation; they contain the reasoning behind every decision below, not just the decisions.

## What this system does

A student solves a math problem by submitting it **step by step** (not free-text, not handwriting — a structured, math-aware input widget per step). The system checks each step **as it's submitted**, and if it's wrong, interrupts immediately (or per a configurable timing policy — see below) rather than waiting for a final answer. It does not just say "wrong" or give the correct step. It diagnoses the *specific misconception* behind the error and guides the student back to a correct step through **multi-turn Socratic dialogue** — asking guiding questions, never handing over the answer — the way an attentive parent corrects a child mid-mistake rather than after the fact.

This is simultaneously meant to be (a) a real, usable product — not a research throwaway — and (b) the basis of a research paper, so build quality, logging, and evaluability all matter from day one, not just "does it work."

## Read these first, in this order

1. `docs/approach.md` — project framing, research novelty/gap, and a section evaluating and revising the founder's own early design decisions. Explains *why* the project is scoped the way it is.
2. `docs/literature_survey.md` — ~45 verified papers across five threads (classic/modern intelligent tutoring systems & knowledge tracing, automated misconception diagnosis, LLM-based Socratic tutoring, feedback-timing psychology, LLM reliability/child-safety). Read the synthesis section at the end especially — it states the exact gap this project fills.
3. `docs/technical_architecture.md` — **this is the primary engineering spec.** It went through a full revision pass (section 0 has a table of every change and the paper that motivated it, sections marked `[REVISED — <citation>]` inline) and section 12/13 has full citations. Build against this document, not from scratch — it already resolved several architecture decisions that would otherwise need re-litigating (e.g. why classification is closed-set not open-ended, why every dialogue turn is a decide-then-generate pair, why there's a deterministic leakage filter, why intervention timing is a configurable policy).

## Non-negotiable architectural principles (do not relitigate these without flagging it to the user first)

- **The LLM is never the sole arbiter of mathematical correctness.** Every step submission is checked by a deterministic symbolic/rule-based verifier (sympy + a per-topic rule engine) before the LLM is ever involved. The verifier is a hard pipeline gate called directly by application code — never a tool the LLM decides when to invoke.
- **Bias toward false negatives over false positives** in the verifier — when confidence is low, don't interrupt, rather than risk wrongly telling a child they're wrong.
- **Error classification is closed-set, not open-ended.** Retrieve candidate misconceptions for the current `(topic, step_type)` from the misconception bank *before* calling the LLM; the LLM picks among them or says "none of these." Never let it freely diagnose.
- **Every dialogue turn is two steps: decide, then generate.** First produce a structured `{error_type, remediation_strategy, instructional_intent}` object grounded in the verified error + retrieved misconception; only then generate the child-facing message conditioned on that object. Don't go straight from error to message.
- **Every generated message passes two deterministic gates before reaching the child:** an answer-leakage filter (string/value-match against the known correct step/answer from the problem schema; reject-and-regenerate on match) and a readability gate (Flesch-Kincaid or similar, targeting a Class 5 reading level; reject-and-regenerate if it fails).
- **Re-verification on every retry.** When a student resubmits a step mid-dialogue, it goes back through the deterministic verifier — never trust the LLM's judgment that "the student seems to get it now."
- **Turn budget with graceful fallback.** Cap dialogue turns per step (e.g. 3–4); after the cap, show a fully worked example rather than leaving the child stuck, and log the step as "escalated."
- **Intervention timing is a configurable orchestrator policy** ("interrupt on first error" / "interrupt after Nth repeat" / "wait for problem completion"), not a hardcoded behavior — this also becomes the mechanism for running the three-condition research study later without special-cased code paths.
- **Step schema is a DAG, not a linear list.** Multiple valid solution paths must be accepted; check the student's step against every reachable node, not just the prescribed next one.
- **Structured, math-aware step input only** (MathQuill-style or per-step-type structured fields) — never parse free-text math strings.
- **Buggy-rule library first, LLM fallback second** for error classification — a large fraction of primary arithmetic errors are enumerable, named, systematic bugs (see literature survey, thread B); only fall back to the (closed-set, confidence-gated) LLM classifier when no known bug signature matches, and route novel/LLM-classified errors to a semi-automated review queue (cluster similar novel errors before human triage) rather than auto-promoting them into the trusted taxonomy.

## Scope for the first build

- **Curriculum source of truth:** NCERT Class 5 CBSE math textbook.
- **Phase 0 (before any verifier code): do a chapter-by-chapter audit of the NCERT Class 5 syllabus** and propose which topic to build the first verifier/misconception-bank slice against — then **stop and confirm the choice with the user before locking it in.** Don't default silently to a choice; the user has deliberately left this open for you to reason through against the syllabus rather than picking without looking. Weigh: how cleanly the topic decomposes into checkable steps (arithmetic/fractions/decimals/LCM-HCF map cleanly to step verification; Data Handling, Patterns, and parts of Geometry don't, and may need a different interaction pattern or later scope), and how well-documented its misconceptions are in the literature survey (`docs/literature_survey.md` thread B — multi-digit subtraction with borrowing has the deepest grounding, going back to Brown & Burton's DEBUGGY and VanLehn's repair theory).
- **Sequence topic coverage, don't try to cover the full syllabus on day one.** Architect every interface (step schema format, verifier interface, error taxonomy, dialogue engine, logging) to be topic-agnostic and ready for the full syllabus, but ship the first working slice against one topic, get it in front of real students, then expand chapter by chapter using the proven pipeline.
- **Multi-turn dialogue**, not single-turn.

## Engineering standards — this is meant to be production-grade, not a prototype

Build with the assumption this will run in a real classroom/pilot with real children's data, and that the codebase needs to survive months of iteration, not just demo once.

- **Backend:** Python, FastAPI, async throughout. Postgres as the primary datastore (problems, step schemas, misconception bank, buggy-rule library, users, sessions, event log — relational/JSONB, no need for a specialized document/graph DB at this scale). Redis for active per-step dialogue-state caching only — Postgres is the durable source of truth. Alembic for migrations, applied via CI, never hand-run against production.
- **Symbolic verification:** sympy plus a small per-topic rule engine behind a uniform `verify_step()` interface (see technical_architecture.md section 3) so adding a new topic means writing a new verifier module, not touching the pipeline.
- **LLM access: Groq API** (fast open-weight model inference), not Anthropic/OpenAI directly. This is a real deviation from what most of the literature-survey papers evaluated (many benchmark GPT-4/Claude-class models specifically), so treat it deliberately, not incidentally: (a) pick a Groq-hosted model that reliably supports structured output / tool-calling / JSON mode, since the whole pipeline (closed-set classification, decide-then-generate, leakage/readability gates) depends on structured output, not free-text parsing — verify this before committing to a model, don't assume it; (b) build the LLM client behind a small provider-agnostic interface (a thin wrapper around "classify", "decide", "generate" calls) so switching models or adding a fallback provider later is a config change, not a rewrite; (c) because Groq-hosted open models may be weaker at exactly the diagnosis/error-localization tasks the literature survey already flags as unreliable even for frontier models (Jin et al. 2024, Srivatsa et al. 2025 — see `docs/literature_survey.md` threads B and C), this if anything *strengthens* the case for leaning on the deterministic verifier and closed-set/topic-constrained classification rather than trusting open-ended LLM judgment — don't loosen those guardrails to compensate for a smaller model, and flag to the user if the chosen model's structured-output reliability looks shaky in testing. No API key is available yet — build and test phases 1–2 (schema, verifier, buggy-rule matching) fully unblocked without any LLM calls; stub/mock the LLM-calling interface with realistic fake responses so the pipeline is testable end-to-end, and wire in real Groq calls once a key is provided. Log every real call (prompt, response, latency, token cost) once wired — this is both an ops necessity and a research artifact.
- **Testing:** a golden regression-test set of (problem, injected wrong step) pairs per topic for the verifier and buggy-rule matcher, run in CI on every change — this layer is deterministic software and should be tested like any other. Separate regression sets for the leakage filter and readability gate (known-leaky drafts that must be caught, known-over-complex drafts that must be caught), tracked as filter precision/recall over time. A behavioral eval harness for dialogue quality (did the student produce a correct retry within budget) as the primary signal, supplemented by periodic rubric/LLM-as-judge rating.
- **Config/secrets:** twelve-factor style — all config via environment variables, a documented `.env.example` committed, real secrets never committed, loaded via a secrets manager in any real deployment.
- **Containerization:** Docker Compose for local dev (API + Postgres + Redis), with the app itself containerized in a way that's deployable as-is — don't build something that only runs on one machine's local setup.
- **CI:** lint + type-check + test on every push (ruff/mypy for Python; if/when a TS frontend exists, eslint + strict TypeScript). Don't let this slip "for now" — retrofitting CI onto an already-large codebase is much more painful than having it from commit one.
- **Logging/observability:** structured (JSON) logging throughout, a health-check endpoint, and the event log (step submitted, verdict, error type, turn, resolution, escalation) as an explicit, deliberately-designed schema from the start — this data is also the research dataset, so don't treat it as an afterthought.
- **Experiment assignment:** condition (immediate / delayed / control) assigned and persisted per student/session in the same event schema from day one, not retrofitted later.
- **Frontend:** a structured step-input widget (math-aware, minimal typing per step — see technical_architecture.md's note on input friction for young learners) plus a streaming chat UI for the dialogue turns, gated on the leakage/readability checks passing before anything streams to the child.

## Compliance note — do not skip

This handles data from children under 18 in India. India's DPDP Act 2023 + DPDP Rules 2025 (Rule 10) require verifiable parental consent and restrict behavioral tracking of children's data — directly relevant to the per-student misconception/knowledge model this system builds. Flag to the user early that qualified legal guidance on this is needed before any real student's data is collected, even in a small pilot — this has consent-flow implications for the product itself, not just paperwork. See `docs/technical_architecture.md` section 10/13 for sources.

## Build sequence (from technical_architecture.md section 11, still valid)

1. Step-schema format + verifier interface finalized; misconception bank + buggy-rule library seeded for the first topic slice.
2. Verifier engine for that slice, regression tests passing before moving on.
3. Error classification (buggy-rule matcher + closed-set LLM fallback) wired to the verifier's output.
4. Dialogue orchestrator: state machine, decide-then-generate, structured output, turn budget, leakage/readability gates, re-verification on retry.
5. Frontend: structured step-input widget + streaming chat UI.
6. Logging/event infra + experiment condition assignment, wired in before any real student touches the system.
7. Small real pilot on the first topic slice; review the novel-error queue; enrich the misconception bank/buggy-rule library from real data.
8. Expand topic coverage within v1 using the proven pipeline.

## Working process — phase by phase, with two living documents

Do not build this end-to-end in one long unsupervised run. Work **phase by phase** following the build sequence below, and stop for the user's review at the end of each full phase before starting the next — don't silently continue into the next phase just because the current one compiles/passes tests, and don't pause more granularly than phase boundaries unless something genuinely ambiguous comes up mid-phase.

**Git:** initialize a git repository if one doesn't exist, and make a real commit at the end of each phase (or at each meaningful unit of work within a large phase) with a clear message describing what changed — don't leave work uncommitted for the user to commit manually. This should give a commit history with the same granularity as `CHANGELOG.md`'s entries.

Maintain two files at the project root, starting from the very first commit, and keep both **continuously up to date as you work** — not just at the end of a phase:

- **`CHANGELOG.md`** — an append-only, date-and-timestamped log of every meaningful change (new module, schema change, dependency added, bug fix, behavior change). Each entry: timestamp, one-line summary, and enough detail that someone reading it later understands what changed without reading the diff. Never rewrite or delete past entries — append.
- **`ARCHITECTURE.md`** — the living record of architectural decisions, distinct from CHANGELOG.md's chronological log of *changes*. Every time you make or revise an architectural decision (choice of library, schema design, why a component works the way it does, a tradeoff you took), add a date-stamped entry recording: what the decision is, why it was made (what alternatives were considered and why they were rejected), and what it affects. When a later decision supersedes an earlier one, don't delete the old entry — mark it superseded, date-stamped, with a pointer to the new entry, so the document shows the project's reasoning evolving over time rather than just its current state. Seed this file from `docs/technical_architecture.md` (it already contains a full set of dated, cited architectural decisions from the planning phase — bring those in as the initial entries) rather than starting it empty.

Update both files as part of the same unit of work as the code change they describe — never as a separate cleanup pass "later." If a phase's review surfaces a change to an earlier decision, that's exactly what `ARCHITECTURE.md`'s supersede mechanism is for.

## How to work with the user on this

Arnav is the founder/researcher on this project — treat him as the domain owner. He has already made and stress-tested several design decisions across three planning conversations (captured in `docs/`); don't silently relitigate them, but do flag it clearly if something in implementation reveals one of those decisions doesn't hold up in practice. When scope or a technical tradeoff is ambiguous, ask rather than assume — this project intentionally balances "real usable product" against "research contribution," and getting that balance wrong in either direction undermines the point of the project.
