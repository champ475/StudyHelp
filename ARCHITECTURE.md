# Architecture Decision Record

Living record of architectural decisions. Distinct from `CHANGELOG.md` (chronological log of *changes*) — this is a log of *decisions*: what was decided, why, what alternatives were considered and rejected, and what it affects. Never delete an entry; superseded decisions are marked as such, date-stamped, pointing at the entry that replaced them.

Seeded from the dated decisions already made during planning, recorded in `docs/technical_architecture.md` (see its own §0 changelog table and inline `[REVISED — <citation>]` markers) and `docs/approach.md` §7. Entries below dated pre-2026-08-13 reflect when the decision was made during planning, transcribed into this file on 2026-08-13.

---

## Pre-implementation decisions (from `docs/technical_architecture.md` and `docs/approach.md`)

### D1 — Two-layer verification: deterministic symbolic/rule-based check before any LLM involvement
**Decision:** Every step submission is checked by sympy + a per-topic rule engine before the LLM is ever invoked. The verifier is a hard pipeline gate called directly by application code — never a tool the LLM decides when to invoke.
**Why:** A pure-LLM checker can mis-grade a correct step as wrong or miss a real error; for a young learner with no way to sanity-check the tutor, an unreliable correction is worse than none. Reinforced by Davis & Aaronson 2023 (E4) — GPT-4 + WolframAlpha + Code Interpreter still failed largely due to "interface failures" (the LLM mis-formulating its own tool query), showing that even giving an LLM a correctness tool doesn't work if the LLM controls when/how to call it. Alternative considered and rejected: let the LLM call a `check_step()` function at its own discretion — rejected because it reintroduces the exact failure mode the two-layer split exists to eliminate.
**Affects:** Verification Service design (§3), pipeline shape (§1): verify → classify → retrieve → converse → re-verify → log.

### D2 — Bias toward false negatives over false positives in the verifier
**Decision:** When verifier confidence is low, don't interrupt, rather than risk wrongly telling a child they're wrong.
**Why:** Wrongly accusing a correct step of being wrong is more damaging to trust than occasionally missing a real error, especially for a 10-year-old who can't push back on the tutor.
**Affects:** Verifier confidence thresholding, must be explicit and tested, not emergent.

### D3 — Error classification is closed-set, not open-ended
**Decision:** Retrieve candidate misconceptions for the current `(topic, step_type)` from the misconception bank before calling the LLM; the LLM picks among them or says "none of these." Never let it freely diagnose.
**Why:** Otero, Druga & Lan 2025 (B7) — GPT-4-turbo misconception accuracy jumped from 52.96% (unconstrained) to 73.82–83.91% (topic-constrained). Jin et al. 2024 (B8) — all 16 tested LLMs scored F1<0.5 diagnosing *why* a student erred, with strong overconfidence specifically on wrong diagnoses (the failure mode is "confidently wrong," not "appropriately unsure").
**Affects:** Error Classification service (§4), Misconception Bank retrieval (§5) — retrieval now runs twice per error (once to constrain classification, once to ground dialogue generation).
**Supersedes:** original design where "LLM fallback classifies novel errors directly into the taxonomy" (see `docs/technical_architecture.md` §0 row 1).

### D4 — Buggy-rule library first, LLM fallback second for error classification
**Decision:** A pattern-matchable library of known buggy rules (Brown & Burton / VanLehn tradition) is checked first; the LLM only classifies when no signature matches.
**Why:** A large fraction of primary arithmetic errors are enumerable, systematic procedural bugs, not random noise (B1–B3). Cheap, deterministic, explainable, and a genuine bridge between classic symbolic ITS research and modern LLM tutoring for the paper's framing.
**Affects:** Error Classification service (§4). Directly motivates the phase-0 topic choice (subtraction-with-borrowing has the deepest buggy-rule literature of any NCERT Class 5 topic).

### D5 — Novel/LLM-classified errors are never auto-promoted into the trusted taxonomy
**Decision:** LLM classifications always carry a lower-confidence flag and route to a semi-automated review queue — similar novel errors clustered before a human reviewer looks, per Feldman et al. 2018 (B4)'s CHI 2018 approach — rather than one-by-one triage or silent auto-promotion.
**Why:** LLM classification overconfidence (D3's Jin et al. citation) means an unsupervised LLM diagnosis can't be trusted at the same tier as a buggy-rule-signature match. Clustering first turns "triage 12 near-duplicate items" into "confirm this cluster is a new bug, once."
**Affects:** Error Classification service (§4) review-queue design; this is the system's data flywheel — confirmed novel bugs get promoted into the buggy-rule library and misconception bank.

### D6 — "Examinee vs. diagnostician" role-framing fix in the classification prompt
**Decision:** Classification prompts must explicitly instruct the LLM that it is not solving the problem — the correct answer is given — its only job is to explain the reasoning path that would produce the *student's* incorrect answer.
**Why:** Song et al. 2026 (B10) named a reproducible failure mode: LLMs asked to explain a wrong answer default to an "examinee" mindset (quietly re-solving) instead of a "diagnostician" mindset (reasoning about why *this* answer is wrong given the student's actual approach).
**Affects:** Error Classification prompt design (§4); becomes an explicit eval case (§9) — does the stated reasoning path match the student's apparent approach, or does it just re-derive the correct answer and note a discrepancy.

### D7 — Every dialogue turn is decide-then-generate, not error-to-message directly
**Decision:** Each turn is two structured calls (or two phases of one call): call 1 outputs `{error_type, remediation_strategy, instructional_intent}` grounded in the verifier's output and retrieved misconception entry; call 2 generates the child-facing `message` conditioned on that decision object.
**Why:** Wang, Zhang, Robinson, Loeb & Demszky 2024 ("Bridge," NAACL, C5) — GPT-4 conditioned on an explicit expert decision framework was preferred 76% more than unconditioned generation; *randomly assigned* decisions (going through the motions without being the right decision) cut quality by 97% vs. expert-informed decisions. The decision content has to actually be right — which is why it's fed by the retrieved, topic-constrained misconception match (D3), not invented fresh each turn.
**Affects:** Dialogue Orchestrator (§6) turn structure; makes strategy-selection independently loggable/evaluable, separate from message wording (§9).
**Supersedes:** original design where the orchestrator "generates a Socratic message directly from (error, misconception context)" (`docs/technical_architecture.md` §0 row 2).

### D8 — Deterministic, per-turn answer-leakage filter
**Decision:** Before any generated message reaches the child, string/value-match it against the known correct step/final answer (and close paraphrases/numeric matches) from the problem schema; reject-and-regenerate on match, with an explicit "don't state the answer" instruction appended to the regeneration prompt.
**Why:** SafeTutors (Hazra et al. 2026, E8) — pedagogical-harm rate (mostly premature answer disclosure) rose from 17.7% at turn 1 to 77.8% by later turns across every tested model; prompting alone is not sufficient once a dialogue runs several turns. Because the system already has ground-truth from the problem schema, this is cheap to check deterministically rather than via a generic moderation pass.
**Affects:** Dialogue Orchestrator (§6) output pipeline; interacts with streaming (only stream after a message passes both gates, never speculatively). Lee et al. 2026's "LeakShield" prompting technique (C10) adopted as first line of defense before the filter has to trigger a (turn-budget-costing) regeneration.
**Supersedes:** original design of "turn-budget cap + one output-safety pass" (`docs/technical_architecture.md` §0 row 3).

### D9 — Measurable readability gate (Flesch-Kincaid or similar), not just a prompt instruction
**Decision:** Run a readability check on every generated message against a target ceiling appropriate for a Class 5 reader; regenerate with an explicit simplification instruction if it fails.
**Why:** Parra, Corica & Godoy 2026 (C13) — LLM tutor responses require a *higher* reading level than human tutors' by default, across every tested model; the model doesn't self-correct without being forced to. Jiao et al. 2025 (E10) — children over-trust AI responses even when wrong, partly *because* of confident/anthropomorphized phrasing, so an over-complex explanation is also more likely to be blindly accepted.
**Affects:** Dialogue Orchestrator (§6) output pipeline, same regenerate-on-fail pattern as D8. Needs its own regression test set (known-over-complex drafts that must be caught), tracked as filter precision/recall (§9).
**Supersedes:** original design of "'age-appropriate tone' as a prompt instruction" (`docs/technical_architecture.md` §0 row 4).

### D10 — Intervention timing is a configurable orchestrator policy, not a hardcoded default
**Decision:** The orchestrator exposes intervention timing as a policy parameter consulted per step — "interrupt on first error" / "interrupt after Nth repeated error on the same step" / "wait for problem completion" — rather than one hardcoded behavior with alternates special-cased for the study.
**Why:** The feedback-timing literature is genuinely unsettled, not a case of "immediate is obviously right with delayed only as a study comparison arm." Kandemir et al. 2026 (D4 in lit survey) found no significant average timing effect in computer-assisted learning specifically (g=0.03); Metcalfe, Kornell & Finn 2009 (D7 in lit survey) found delayed feedback beat immediate for children on a (declarative) learning task; Young, Bevan & Sanders 2024 (D10 in lit survey) found the productive-struggle literature hasn't resolved when outside intervention helps vs. short-circuits useful struggle.
**Affects:** Dialogue Orchestrator (§6) state machine; directly simplifies running the three-condition RCT later, since conditions become policy configs rather than special-cased code paths. Experiment Assignment service (§8) persists the assigned condition per student/session from day one.
**Supersedes:** original design where "immediate interruption" was implicitly the hardcoded default (`docs/technical_architecture.md` §0 row 7).

### D11 — Step graph (DAG), not a linear step list
**Decision:** Problems are authored with a DAG of acceptable intermediate states, not a single prescribed sequence. The verifier checks the student's step against every reachable node, not just the immediate expected successor. A match against a non-adjacent-but-valid node is accepted but flagged for review, not silently accepted or rejected.
**Why:** Class 5 problems often have more than one legitimate solution path. Shih et al. 2023 (A8/D9 in lit survey)'s own deployed fractions ITS explicitly couldn't capture "all possible patterns of learners' responses" because it matched against a fixed pattern library instead of a full graph — real evidence, not a theoretical concern, that this failure mode bites in practice.
**Affects:** Problem/step-schema representation (§2), Verification Service (§3).

### D12 — Structured, math-aware step input only, never free-text math parsing
**Decision:** Students submit steps through a math-aware input widget (MathQuill-style or per-step-type structured fields) that emits an unambiguous structured value (small JSON AST or constrained LaTeX subset) — never a raw string to be parsed.
**Why:** Sidesteps an entire class of notation-ambiguity bugs (implicit multiplication, fraction-bar parsing, sign placement) that would otherwise consume a large fraction of engineering time for little research value.
**Affects:** Frontend step-input widget (§2, §11 build sequence step 5), Verification Service input contract (§3).

### D13 — Typing friction is a documented UX failure mode for this age group
**Decision:** Minimize keystrokes per step at the widget level (numeric keypad, drag-to-place-digit, tap-to-select from a small candidate set wherever the step type allows); track time-to-submit-a-step as a pilot UX metric.
**Why:** Shih et al. 2023 (A8)'s real 6th-grade deployment explicitly reported keyboard/mouse input as "time-consuming and inconvenient," causing impatience.
**Affects:** Frontend step-input widget design (§2); pilot instrumentation (§9, §11 build sequence step 7).

### D14 — Turn budget with graceful fallback
**Decision:** Cap dialogue turns per step (3–4). After the cap, show a fully worked example and let the student proceed, logging the step as "escalated."
**Why:** Open-ended multi-turn dialogue risks a frustration loop if the child still doesn't get it after several tries (`docs/approach.md` §7). Escalation rate is itself a useful research signal — how often dialogue alone fails to get the student there.
**Affects:** Dialogue Orchestrator (§6) state machine.

### D15 — Re-verification on every retry, never LLM self-assessment
**Decision:** When a student resubmits a step mid-dialogue, the resubmission goes back through the deterministic Verification Service (D1), never through the LLM's judgment of whether the student "seems to get it now."
**Why:** Keeps multi-turn dialogue from drifting away from the grounding that made single-turn correction reliable in the first place; the two-layer verification idea otherwise only really protects the first correction.
**Affects:** Dialogue Orchestrator (§6) `AwaitingRetry` state transition.

### D16 — Attention-based (SAKT-style), not recurrence-based (DKT/LSTM), if/when a learned knowledge-tracing model is justified
**Decision:** v1 uses a simple, explainable mastery score (basic BKT update or decaying success-rate counter), not a deep KT model. *If* v2 data volume justifies a learned model, prefer an attention-based architecture (SAKT) over LSTM-based DKT.
**Why:** RNN-based KT models need long interaction histories; a single Class-5 tutoring session is far shorter/sparser than DKT's benchmark datasets (thousands of interactions/student). Pandey & Karypis 2019 (A3 sub-bullet) reported SAKT ~4.4% average AUC improvement over DKT-family baselines specifically on sparse-history data.
**Affects:** Student Model (§7) — v1 scope explicitly excludes deep KT; only changes what "v2" should reach for.
**Supersedes:** original doc's generic "DKT/LSTM" naming as the eventual upgrade path (`docs/technical_architecture.md` §7 revision note).

### D17 — LLM provider: Groq, not Anthropic/OpenAI
**Decision:** LLM access goes through the Groq API (fast open-weight model inference), behind a provider-agnostic wrapper (thin interface around "classify" / "decide" / "generate" calls) so switching models or providers is a config change, not a rewrite. Model selection must verify structured-output/tool-calling reliability before committing, not assume it. No key available yet — phases 1–2 (schema, verifier, buggy-rule matching) build and test fully unblocked with no LLM calls; the LLM-calling interface is stubbed with realistic fake responses until a key is provided.
**Why:** Explicit project-level instruction (`CLAUDE.md`). This is a real deviation from most of the literature survey's evaluated models (GPT-4/Claude-class), so it's treated deliberately: because Groq-hosted open models may be weaker at exactly the diagnosis/error-localization tasks the survey already flags as unreliable even for frontier models (Jin et al. 2024, B8; Srivatsa et al. 2025, C12), this *strengthens* rather than loosens the case for the deterministic verifier and closed-set classification (D1, D3) — guardrails don't get relaxed to compensate for a smaller model.
**Affects:** LLM client design (§8), every LLM-touching service (§4, §6). All real Groq calls, once wired, are logged in full (prompt, response, latency, token cost).
**Supersedes:** `docs/technical_architecture.md` §8's line "LLM access: Claude via API, structured/tool-output mode..." — that line reflected an earlier planning-stage assumption and was never updated in the source doc. Superseded 2026-08-13, before any implementation, per explicit instruction in `CLAUDE.md`.

### D18 — DPDP Act 2023 / DPDP Rules 2025 compliance is a pre-pilot gate, not a paperwork footnote
**Decision:** Qualified legal guidance on DPDP compliance (verifiable parental consent, Rule 10 restrictions on behavioral tracking of children's data) is required before any real student's data is collected, even a small pilot. This has consent-flow implications for the product itself (e.g., a parental-consent gate before a child's account can generate logged data), not just paperwork to file separately.
**Why:** The system handles data from children under 18 in India; the per-student misconception/knowledge model (Student Model, §7) is exactly the kind of behavioral tracking the DPDP Rules target.
**Affects:** Pilot planning (§11 build sequence step 7), Student Model / Event Log design (§7, §8) — flagged to Arnav early per `CLAUDE.md`'s compliance note, not deferred.

---

## Project-scoping decisions (from `docs/approach.md` §7 and `CLAUDE.md`)

### D19 — Sequence topic coverage; don't build the full syllabus before shipping
**Decision:** Architect every interface (step schema, verifier interface, error taxonomy, dialogue engine, logging) topic-agnostic and ready for the full syllabus, but ship the first working slice against one topic, pilot it, then expand chapter by chapter.
**Why:** Symbolic verification effort is not uniform across topics (arithmetic is cheap, geometry/data-handling/patterns are each their own hard problem). For the research study specifically, coverage breadth actively hurts statistical power — narrower topic coverage with more repetitions per error type beats shallow coverage of everything. "Architecture is topic-agnostic, ships N of M chapters" is not in tension with "built for full Class 5 math" as a product claim.
**Affects:** Overall build sequence (`docs/technical_architecture.md` §11); directly produced the phase-0 topic audit (2026-08-13 entry, `CHANGELOG.md`).

### D20 — First-slice topic: NCERT Class 5 Chapter 1, multi-digit subtraction with borrowing
**Decision:** The first verifier/misconception-bank slice targets subtraction with borrowing on large numbers (NCERT Ch.1, "The Fish Tale"), confirmed by Arnav on 2026-08-13 after a chapter-by-chapter audit of all 14 NCERT Class 5 Math-Magic chapters.
**Why:** Of all 14 chapters, this one has by far the deepest misconception-literature grounding (Brown & Burton's DEBUGGY, VanLehn's repair theory — B1–B3) and one of the cleanest step-DAG decompositions. Runners-up considered: Ch.13 long division (richest step-DAG in the syllabus, but the survey's specific bug-tradition citations center on subtraction) and Ch.6 LCM/HCF (also clean, weaker literature grounding). Chapters ruled out for v1 step-verification: Shapes and Angles, How Many Squares?, Does it Look the Same?, Can You See the Pattern?, Mapping Your Way, Boxes and Sketches, Smart Charts — these are recognition/visual/interpretive tasks, not linear checkable procedures, matching the caveat already flagged in `docs/approach.md` §7.
**Affects:** Phase 1 (`docs/technical_architecture.md` §11 step 1) — step schema, verifier, and misconception bank all built first against this topic. See full audit table in `CHANGELOG.md`, 2026-08-13 09:15 entry.

### D24 — Buggy-rule matching is direct Python predicates, not a formula-string interpreter
**Decision:** `classification/rule_matcher.py` implements each of the four seeded buggy-rule signatures (B1-B4) as a dedicated, testable Python function operating on a `(correct_fields, student_fields)` pair — it does not `eval()` or otherwise interpret the seeded `buggy_rule_library.signature_matcher` JSON's `student_formula` string at runtime.
**Why:** Evaluating an arbitrary formula string is both a security liability (even against trusted seed data, it invites scope creep toward evaluating less-trusted input later) and harder to test/debug than a plain function. The seeded declarative JSON remains valuable as the reviewable, citable artifact (technical_architecture.md §4's "genuine bridge between classic symbolic ITS research and modern LLM tutoring") — this decision just means the JSON documents the pattern for humans while the Python function is the actual executable check, and the two are kept in sync by a cross-matrix test (`test_rule_matcher.py`) that verifies each matcher fires on its own seeded `example_pair` and *not* on any other bug's.
**Affects:** `classification/rule_matcher.py`. A genuinely general formula DSL is a fair v2 idea if the buggy-rule library grows large enough that hand-writing a Python predicate per bug stops scaling — not needed at 4 bugs / 1 topic.

### D25 — LLM client: three-method Protocol built now, logging centralized in a wrapper, Groq provider written but gated unusable without a verified model
**Decision:** `llm/client.py` defines the full `LLMClient` Protocol (`classify`/`decide`/`generate`) even though Phase 2 only calls `classify()` — `decide`/`generate` are stubbed to raise `NotImplementedError` in `GroqLLMProvider` until Phase 3. Every call, from any provider, is logged (prompt, response, latency, cost) by a single `LoggingLLMClient` wrapper rather than duplicated per-provider logging code. `build_llm_client()` raises immediately if `LLM_PROVIDER=groq` is set without both `GROQ_API_KEY` and `GROQ_MODEL` — there is no default model to silently fall back to.
**Why:** CLAUDE.md's explicit instruction to build the provider-agnostic interface up front, log every real call once wired, and never assume a Groq model's structured-output reliability without verifying it directly. Making the "no model configured" case a hard `RuntimeError` (not a silently-chosen default) is what actually enforces the "verify before use" instruction in code, not just in a comment.
**Affects:** `llm/client.py`, `llm/providers/mock.py` (default provider, fully tested, deterministic on purpose so tests don't need to tolerate randomness), `llm/providers/groq.py` (written to the shape of Groq's OpenAI-compatible JSON-mode chat-completions API, **not verified against a live API** — no key exists yet; smoke-tested only for constructibility, not for real structured-output behavior).
**Open task, not yet done:** once a Groq key is provided, directly test the chosen model's structured-output/tool-calling reliability before relying on it anywhere beyond local supervised testing, per CLAUDE.md.

### D26 — Classification orchestrator: rule match short-circuits before any DB/LLM access; closed-set validation happens in application code regardless of provider
**Decision:** `classification/classifier.py`'s `classify_error()` tries the buggy-rule matcher first; only if nothing matches does it retrieve misconception-bank candidates and call the LLM. The LLM's returned `misconception_id` is checked against the exact retrieved candidate-id set in application code — any id outside that set (or `None`) is routed to the novel-error review queue, never trusted as-is. LLM-sourced classifications always carry `confidence="low"`; only rule matches carry `confidence="high"`.
**Why:** Direct implementation of D3/D4/D5. Short-circuiting on a rule match before touching the DB or LLM keeps the common case (a known bug) cheap and fast, and keeps the rule-match path unit-testable without any DB/network dependency (`tests/unit/classification/test_classifier.py`) — only the LLM-fallback path needs integration-test coverage against a real Postgres.
**Affects:** `classification/classifier.py`, `db/repositories/misconception_repository.py` (retrieve-don't-dump — only `(topic, step_type)`-scoped candidates are ever loaded), `db/repositories/novel_error_repository.py`.

### D27 — Novel-error clustering: a stable structural-signature string, not ML
**Decision:** `classification/clustering.py`'s `cluster_signature(topic, step_type, discrepant_fields)` produces a deterministic key (sorted discrepant-field names + a short hash) used to group `novel_errors` rows. `cluster_pending_novel_errors()` assigns this signature to every unclustered row and is idempotent (already-clustered rows are untouched; re-running clusters nothing new).
**Why:** Feldman et al. 2018's clustering-before-human-review approach (D5) doesn't require anything more sophisticated at this scale — "same topic, same step type, same fields disagreed" is already a meaningful, cheap grouping that turns "review 12 near-duplicate novel errors" into "confirm this one cluster is a new bug." A real similarity-embedding approach is a reasonable v2 if/when the novel-error volume from a real pilot makes a plain structural key too coarse — not needed yet, and not build-time-blocking for Phase 2.
**Affects:** `classification/clustering.py`, `db/models/novel_error.py` (migration `0002_novel_errors.py`). Promoting a confirmed cluster into `buggy_rule_library`/`misconception_bank` is explicitly out of scope here — that's Phase 6 (real pilot), per the approved build plan.

### D28 — Dialogue state machine: only `AwaitingRetry` and a tracking-only `ErrorDetected` are ever persisted between calls
**Decision:** `dialogue/state.py`'s persisted `DialogueState` really only takes two meaningfully-different forms across calls: `AwaitingRetry` (an active dialogue mid-turn, with a real conversation and a nonzero `turn_count`) and a `ErrorDetected` tracking-only record (no conversation, `turn_count` stays 0) used purely to persist `consecutive_errors_on_this_step` across calls where the timing policy decided *not* to intervene yet. `Explaining` is a transient, in-request-only step of producing a turn, never itself written to Redis. A correct submission always deletes whatever's there, whether that's a real dialogue (→ `resolved`) or just tracking (→ plain `no_action`).
**Why:** A real bug surfaced during testing: the first implementation didn't persist anything at all when the timing policy said "don't intervene yet," which meant `AFTER_NTH_REPEAT` could never actually reach its threshold — every subsequent call saw an empty state and reset the count back to 1. `test_after_nth_repeat_policy_waits_for_the_second_wrong_attempt` (`tests/unit/dialogue/test_orchestrator.py`) caught this on first run. The fix persists a minimal tracking record even in the no-intervention path, keyed by the same `(session_id, problem_id)` Redis key as the real dialogue state.
**Affects:** `dialogue/orchestrator.py`, `dialogue/state.py`. This is exactly the kind of correctness bug the plan's "run it, don't just write it" testing philosophy is meant to catch before a policy like `AFTER_NTH_REPEAT` — one of the three arms the eventual RCT needs — silently never worked.

### D29 — Dialogue-gate testing uses `fakeredis`, not a live Redis server
**Decision:** Unit tests for `dialogue/state.py` and `dialogue/orchestrator.py` run against `fakeredis.FakeAsyncRedis` — an in-memory, Redis-protocol-compatible implementation — rather than skipping gracefully the way Postgres-dependent integration tests do.
**Why:** This sandboxed dev environment has neither Docker nor a local Redis install (same constraint noted for Postgres since the Phase 1 DB-layer commit). Unlike Postgres, where a graceful-skip pattern was the pragmatic choice (SQL dialect/constraint behavior genuinely needs a real Postgres to verify), Redis usage here is simple enough (get/set/delete with JSON string values) that a well-maintained fake client gives *real* coverage of the actual state-machine logic — which is the most important, most bug-prone part of Phase 3 — rather than 100% of dialogue-state tests skipping locally. `docker-compose.yml`'s real Redis service remains what's used in the actual dev/deploy environment; `fakeredis` is a test-only dependency.
**Affects:** `pyproject.toml` dev dependencies (`fakeredis`), `tests/unit/dialogue/test_state.py`, `tests/unit/dialogue/test_orchestrator.py`.

### D30 — SSE event stream separates structured diagnostic events from the one gated child-facing text event
**Decision:** `POST /sessions/{id}/steps` streams four event types: `verdict` and `classification` (structured, internal/diagnostic — not gated, since they're not generated prose shown as a tutor message), `message_chunk` (the only event carrying LLM-generated child-facing text, emitted only after `handle_step_submission()` has already cleared both output gates), and `turn_complete` (final structured summary). "Streaming" for now means word-chunking an already-fully-vetted complete message string, not real token streaming.
**Why:** technical_architecture.md §6's "never stream an unvetted draft" rule applies specifically to generated dialogue text — not to structured verifier/classifier output, which was never a candidate for leakage/readability gating in the first place (it's not prose a child reads). Keeping these as separate, clearly-labeled event types means a real chat UI (Phase 4) can choose to render only `message_chunk`/`turn_complete.message` as tutor bubbles and ignore `verdict`/`classification` as the diagnostic channel they are, rather than the gate boundary being implicit or easy to violate by accident.
**Affects:** `api/routes/sessions.py`. Real Groq token streaming (once a key exists) replaces the post-hoc word-chunking without changing the SSE event shape — `message_chunk` events would just start arriving incrementally from the actual `generate()` call instead of being sliced from a complete string after the fact.

---

## Implementation-phase decisions (from the approved Phase 1–4 build plan, 2026-08-13)

### D21 — Repo layout: `backend/` (Python) and `frontend/` (React/TS) as siblings from commit one; `verification/topics/<topic>/` as the per-topic extension point
**Decision:** All Python lives under `backend/src/studyhelp/`, with `frontend/` created as an empty placeholder immediately rather than added later. Within the backend, each pipeline stage gets its own package (`db/`, `schemas/`, `verification/`, `classification/`, `dialogue/`, `llm/`, `api/`, `seed/`); `classification/` and `dialogue/` exist as empty stub packages from Phase 1 even though they're not filled in until Phases 2–3. Adding a new topic to the verifier means adding a new module under `verification/topics/<topic>/` against the shared `StepVerifier` interface — never touching pipeline code.
**Why:** Avoids a painful path/CI/Docker-context restructure when Phase 4's frontend actually lands (`frontend/` already exists, already has its own place in `docker-compose.yml`'s eventual shape). Stub packages for later phases mean Phase 2/3 slot in without moving files Phase 1 code already imports from. This is the concrete mechanism behind the already-settled "adding a topic = new verifier module, not touching the pipeline" principle (`CLAUDE.md`, D1).
**Affects:** All backend code; directly followed from a Plan sub-agent's design pass grounded in `docs/technical_architecture.md` §§1–3.

### D22 — Confidence thresholds are named constants with dedicated test coverage, not implicit behavior
**Decision:** `ACCEPT_THRESHOLD=0.9` and `REJECT_THRESHOLD=0.75` are named constants in `verification/confidence.py`. Exact frontier match → valid, high confidence. Exact non-adjacent-but-graph-valid match → valid, flagged `non_adjacent_valid_match` (accepted, not silently absorbed — surfaced for review per D11). Unambiguous field mismatch scoring ≥ `REJECT_THRESHOLD` confidence-of-wrongness → invalid. Anything in the band between the two thresholds, or genuinely ambiguous → **don't interrupt** (`low_confidence_passthrough`), but still logged as an event so the threshold can be tuned from real data later.
**Why:** Makes D2's "bias toward false negatives" an actual tested code path with its own golden-suite cases, not an emergent property nobody can point to in a review. A malformed/nonexistent step type is the one exception carved out of the false-negative bias — that's a structural error, not an ambiguous math judgment, so it always rejects regardless of confidence.
**Affects:** `verification/confidence.py`, `verification/topics/subtraction_borrowing/verifier.py`, golden regression suite (dedicated pass-through test cases).

### D23 — `verify_step()`'s procedural correctness is custom graph/state-machine logic; sympy's role is narrow and explicit
**Decision:** For subtraction-with-borrowing, sympy is used for exactly two things: (a) an independent cross-check of the final arithmetic identity (`minuend - subtrahend == final_answer`) that doesn't trust the graph-walk alone, and (b) per-step arithmetic identities within a candidate node (e.g. `to_digit_after == to_digit_before + 10`). Whether the *right procedural move happened in the right place* — was a borrow needed here, did the student borrow from the correct column, does this step land on a valid DAG node — is custom Python logic (candidate search over graph nodes + per-step-type field checkers), not sympy.
**Why:** Being explicit about this split matters: sympy's arithmetic contribution for plain integer subtraction is fairly thin on its own (plain ints would mostly do), so its real value here is (i) a shared, reusable arithmetic-identity utility that later topics (fractions, LCM/HCF) will lean on far more heavily, and (ii) a second, independent check on the final answer that doesn't trust the DAG-walk as the only source of truth. Avoids the false impression that "sympy verifies subtraction-with-borrowing" when the actual procedural verification is bespoke.
**Affects:** `verification/topics/subtraction_borrowing/sympy_utils.py`, `step_checkers.py`.
