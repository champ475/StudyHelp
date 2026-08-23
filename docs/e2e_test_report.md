# End-to-end test report — `fix/tutor-hand-holding`

Date: 2026-08-23. Scope: verification of Issues A/B/C fixes (this round) plus a
broad regression sweep across every seeded topic, run against the live SSE
API (`POST /sessions/{id}/steps`) on a mock-backed dev server, with two
targeted browser (Playwright) checks for UI-only concerns. Not exhaustive —
one representative problem per topic, not all ~140.

## How this was run

- Backend: `LLM_PROVIDER=mock`, fresh reseeded Postgres (`alembic downgrade
  base && upgrade head && scripts/seed_db.py`), Redis via `docker compose`.
- A Python script (`e2e_sweep.py`, not committed — scratch tooling) drove the
  real SSE endpoint for one problem per topic, deriving the canonical
  correct-text sequence directly from each topic's fixture JSON (reusing the
  same render logic each topic's own `test_*_fixtures_walkthrough.py` already
  uses and has verified). Five scenarios per topic: clean correct run,
  wrong-then-correct retry, repeated-same-error, skip-ahead-to-final-answer,
  and (implicit in the retry scenario) the post-resolution concept-check.
- Two Playwright screenshots against the same server for UI-only checks
  Issue A/B/C's fixes needed a real browser to confirm, plus the same fixed
  Groq-backed reproduction session used to root-cause Issue A (see below).

## Issue A/B/C fixes: verification

**Issue A (fractions_addition fallback message)** — root-caused live against
the *real* Groq provider (`openai/gpt-oss-120b`), not mock: mock's static
templates contain no digits at all and could never have reproduced this.
Confirmed exact mechanism: `GENERATE_SYSTEM_PROMPT` rule 1 (added for
Bug2 last round) tells the model it may use a worked demo example with
different numbers; the model doesn't reliably know which of `correct_step`'s
numbers are secret vs. visible input, so it sometimes picks small
illustrative numbers ("1/2 + 1/3") that coincidentally collide with this
problem's own protected values. Fixed by giving `generate()` the exact
`protected_values` list explicitly (not just the full `correct_step` dict),
both in the system prompt and in the regeneration feedback. Verified via two
new unit tests using a fake capturing `LLMClient` (mock can't exercise this,
by design — see above): `protected_values` is threaded into every attempt
from turn 1, and a leakage-rejected draft that reuses a protected number
inside a demo can still recover on retry rather than guaranteeing 3
rejections. Status: **FIXED**, verified via targeted unit tests (root cause
requires a real LLM to observe directly; not re-verified against live Groq
after the fix, to avoid further API spend — see "Not verified" below).

**Issue B (patterns skip-ahead)** — root-caused: `patterns` (Ch.7) is the
one light-check topic whose problems are a genuine 2-step DAG
(`patterns_common_difference` -> `patterns_next_term`), and the shared
light-check verifier searched only the immediate frontier, unlike the 6
heavy DAG topics (which got this fix last round, D59). Fixed by applying
the same `Problem.reachable_step_ids()` widening to `_light_check/base.py`,
plus sharpened the two `patterns` step-type hint descriptions. Verified via
4 new unit tests (`test_light_check_verifier.py`) and confirmed live in the
sweep below (`patterns`: `skip_ahead_final_answer.matched_is_terminal: true`)
and in a browser screenshot. Status: **FIXED**.

**Issue C (concept-check has no way to answer)** — reframed the message from
interrogative ("why do you think that works?") to reflective ("take a moment
to think about why that works, then let's move on"), in the real prompt, the
mock provider, and the deterministic fallback, and added a visible UI
distinction (dashed border, italic, 💭 marker, `frontend/src/index.css`
`.reflection`) so the message never reads as something requiring a typed
reply. Confirmed live in a browser screenshot — the message renders visibly
as a passing aside, and the next step's input box is already active
immediately below it. Status: **FIXED**, but see finding #1 below — a
separate, unrelated bug this same screenshot surfaced.

## Broad sweep results (all 14 topics)

| Topic | Clean run | Wrong→correct (concept-check) | Repeated error → analogy | Skip-ahead-to-final |
|---|---|---|---|---|
| subtraction_with_borrowing | PASS | PASS, reflective, no "?" | PASS (trading-coins analogy) | PASS, terminal |
| fractions_addition | PASS | PASS | PASS (pizza analogy) | PASS, terminal |
| lcm_hcf | PASS | PASS | PASS (buses analogy) | PASS, terminal |
| decimals | PASS | PASS | PASS (rupees/paise analogy) | PASS, terminal |
| area_perimeter | PASS | PASS | PASS (garden analogy) | PASS, terminal |
| multiplication_division | PASS | PASS | PASS (counters analogy) | PASS, terminal |
| measurement | PASS | PASS | PASS (weighing-scale analogy) | PASS, terminal |
| patterns | PASS | PASS | N/A — no analogy library entry (see #2) | PASS, terminal |
| shapes_angles | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |
| how_many_squares | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |
| symmetry | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |
| mapping | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |
| boxes_sketches | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |
| smart_charts | PASS | PASS | N/A — no analogy library entry | N/A (1-step) |

"PASS" for the analogy column means: the topic has a `llm/analogies.py`
entry and the second identical wrong attempt correctly switched to it,
verbatim, with no "?" or leakage/readability rejection. "N/A" means the
topic has no library entry (by original design, D60 — only the 7 heavy DAG
topics were given one); confirmed the register-switch machinery didn't
crash or misfire for these, it just has nothing to switch to (see #2).

Raw output (every scenario's full verdict/message text, ~14 topics) is
attached to this branch's PR discussion, not committed to the repo.

## Findings for the next round (prioritized)

**1. (High) Light-check topics never trigger the frontend's "solved" state —
the student is left staring at a phantom, permanently-open step box even
after correctly finishing the problem.** `ProblemSolver.tsx`'s `solved`
detection is hardcoded to `node.type === "write_final_answer"` — the type
name only the 7 heavy DAG topics use. Every light-check topic's terminal
node uses a topic-specific type name instead (`patterns_next_term`,
`shapes_angles_answer`, etc.), so `solved` never becomes `true` for any of
the 7 light-check chapters (roughly half the syllabus by chapter count) —
confirmed live in a browser screenshot (`patterns`, 2, 4, 6, 8, ...): after
correctly answering both steps, "Steps completed: 1" and a `Step 2` input
box with a "Type this step" placeholder is still shown, waiting for input
the DAG has no more use for. **Not fixed in this round** — found via this
round's browser screenshot for Issue B, out of the three named issues'
scope; flagging for explicit sign-off before touching it, per this round's
own process. Likely fix: key `solved` off `next.length === 0` on the
matched terminal node instead of a hardcoded type string (mirrors the
backend's own `problem_is_complete` check in `api/routes/sessions.py`,
which already uses `not target_node.next`, not a type-name check — the
frontend drifted from that pattern).

**2. (Medium) 7 of 14 topics have no analogy-library entry, so a student
stuck on the same light-check mistake twice gets the exact same words
twice, verbatim (mock) or a generically-varied-but-not-topic-grounded
re-explanation (real LLM).** By original design (D60) only the 7 heavy DAG
topics got a `llm/analogies.py` entry — the light-check family's
"recognition, not procedure" framing made an analogy feel like a less
obvious fit at the time. Worth reconsidering now that the repeat-count
machinery is broader (D63): even a single generic "try picturing it a
different way" register switch, or a short library entry per light-check
topic (e.g. shapes_angles → clock-hands-and-corners, symmetry →
paper-folding), would likely help more than repeating the identical
sentence.

**3. (Low) Mock provider's non-analogy "procedural/conceptual" branch is a
single static string regardless of `hint_level`.** The "careless" branch
already varies by `hint_level` (3 different short nudges); the longer
re-teach branch doesn't, so two different topics' first-ever mistake
produce identical generic phrasing in dev/mock testing (confirmed in the
sweep table above — several topics show byte-identical "Let's slow down and
look at the idea behind this step..." text). Cosmetic for the real Groq
path (which does vary genuinely per topic/step, confirmed during Issue A's
root-cause session), but makes mock-only manual testing harder to
distinguish topics by feel. Low priority — mock is explicitly a
deterministic stand-in, not the real experience.

**4. (Low) `_protected_values()`'s float-precision-flavored confidence
values** (e.g. `0.19999999999999996` observed for a fractions near-match)
are cosmetically ugly in logs/API responses but not incorrect — plain
floating-point division artifact, not a threshold bug (still correctly
below/above `REJECT_THRESHOLD`/`ACCEPT_THRESHOLD` either way). Not worth
fixing on its own; would be free to clean up if that code is touched for
another reason (e.g. `round(agreement, 4)` at the point of construction).

## Not verified / explicitly out of scope this round

- Issue A's fix was **not** re-run against the real Groq provider after the
  fix landed (the root-cause session already used real API calls and hit a
  rate limit; re-running the exact fractions_addition scenario again was
  judged not worth the additional spend given the fix is a straightforward,
  independently-unit-tested prompt/data change). If a maintainer wants to
  confirm this specific fix against a live model, rerun the same
  `fractions-add-001`, wrong-step-then-repeat scenario from this report's
  Issue A section with `LLM_PROVIDER=groq`.
- Only one problem per topic was swept (not all ~140 seeded problems) — the
  five scenarios were chosen to match this round's request, not to be a
  full regression suite (the existing golden/unit test suites already cover
  per-problem arithmetic correctness).
- `AFTER_NTH_REPEAT`/`WAIT_FOR_COMPLETION` timing policies were not
  exercised in this sweep (the frontend always sends `IMMEDIATE`, and unit
  tests already cover the other two policies directly).

---

## Round 2 (2026-08-23, later) — all 4 findings fixed, re-swept

Fixed all 4 findings from the round-1 list above, then re-ran the same kind
of broad sweep plus targeted browser checks specifically for the "solved"
fix. Method unchanged from round 1 (mock-backed dev server, `e2e_sweep.py`,
Playwright screenshots) except where noted.

### What was fixed

**Finding 1 (light-check "solved" never fires) — FIXED.** `ProblemSolver.tsx`'s
`solved` detection now keys off `next.length === 0` on the matched terminal
node, not the hardcoded `write_final_answer` type string — mirrors the
backend's own `problem_is_complete` check, which never used a type-name
check in the first place.

**Finding 2 (7 light-check topics have no analogy entry) — FIXED, with a
self-inflicted bug caught and fixed along the way.** Added all 7 entries to
`llm/analogies.py` (patterns → staircase, shapes_angles → clock hands,
how_many_squares → chessboard, symmetry → paper folding, mapping →
directions to a friend, boxes_sketches → unfolded cardboard, smart_charts →
jars of marbles). First live check (browser, `shapes_angles`, repeated wrong
answer) found the *new* `shapes_angles` analogy itself triggering the
`_FALLBACK_MESSAGE` — root cause: the draft analogy named the classification
words "acute"/"right"/"obtuse" directly, and `shapes_angles`' actual
possible answers are exactly that closed word set, so the analogy leaked
the real answer whenever it matched (confirmed: the specific test problem's
real answer was "acute"). This is structurally the same class of bug as
Issue A (a demo/explanation using a word or number that coincidentally
equals a real protected value), just for a light-check topic's word-shaped
answers instead of a heavy topic's numeric ones. Fixed by rewriting the
`shapes_angles` analogy to describe the concept structurally (a clock's
hands making a wider or narrower corner) without ever naming a category
label. A second, milder version of the same class of bug was caught by a
new regression test before it ever reached a screenshot: the `symmetry`
analogy's word "nothing" contains "no" as a substring, and some symmetry
problems have a literal answer of "no" — `contains_leakage()` does plain
substring matching, so "nothing" would have falsely collided. Reworded to
avoid the substring "no" entirely. Both fixes verified: a new test,
`test_no_light_check_analogy_collides_with_that_topics_own_answer_words`
(`tests/unit/llm/test_analogies.py`), checks every light-check analogy
against every one of that topic's own seeded answer values, using the same
check the real leakage filter applies — this is now a permanent regression
guard for future analogy edits, not just a one-time fix. Re-verified live
in the browser afterward: `shapes_angles`' second wrong attempt now
switches to the clock analogy with no fallback.

**Finding 3 (mock's procedural/conceptual branch was one static string) —
FIXED.** Added `GenerateRequest.topic` (mirrors `DecideRequest.topic`,
threaded from `dialogue/orchestrator.py` at both call sites, serialized in
`llm/providers/groq.py`). `llm/providers/mock.py`'s non-analogy branch now
varies by both topic (a short `_TOPIC_FOCUS` phrase per topic, e.g. "how
the parts fit together" for fractions, "how the angle is shaped" for
shapes_angles) and `hint_level` (3 different sentence structures, same
mechanism the "careless" branch already used) — confirmed in the re-swept
sweep table below that no two topics' first-attempt message is
byte-identical anymore.

**Finding 4 (float-precision noise in confidence values) — FIXED.** All 6
heavy topics' `step_checkers.py::compare_to_expected()` now round
`agreement` to 4 decimal places at construction, and their `verifier.py`'s
`confidence=1.0 - agreement` near-match construction rounds the result too
(rounding `agreement` alone doesn't prevent `1.0 - 0.8` producing
`0.19999999999999996` — Python float subtraction, not the division that
produced `0.8`). `subtraction_borrowing`'s `step_checkers.py` was rounded
too for consistency (its verifier uses `agreement` directly as confidence,
no subtraction, so it never showed the artifact, but a future change that
did subtract from it would have). Confirmed in the re-swept sweep's raw
verdict data — every confidence value observed is now a clean, short
decimal (`0.2`, `0.3333`, `0.5`, `0.75`, `0.85`, `1.0`), no float noise.

### Re-sweep results (all 14 topics, all 5 scenarios)

Full re-run of the round-1 sweep, after all 4 fixes:

| Topic | Clean run | Wrong→correct (concept-check) | Repeated error → analogy | Skip-ahead-to-final |
|---|---|---|---|---|
| subtraction_with_borrowing | PASS | PASS, reflective, no "?" | PASS (trading-coins analogy) | PASS, terminal |
| fractions_addition | PASS | PASS | PASS (pizza analogy) | PASS, terminal |
| lcm_hcf | PASS | PASS | PASS (buses analogy) | PASS, terminal |
| decimals | PASS | PASS | PASS (rupees/paise analogy) | PASS, terminal |
| area_perimeter | PASS | PASS | PASS (garden analogy) | PASS, terminal |
| multiplication_division | PASS | PASS | PASS (counters analogy) | PASS, terminal |
| measurement | PASS | PASS | PASS (weighing-scale analogy) | PASS, terminal |
| patterns | PASS | PASS | PASS (staircase analogy) | PASS, terminal |
| shapes_angles | PASS | PASS | PASS (clock-hands analogy) | N/A (1-step) |
| how_many_squares | PASS | PASS | PASS (chessboard analogy) | N/A (1-step) |
| symmetry | PASS | PASS | PASS (paper-folding analogy) | N/A (1-step) |
| mapping | PASS | PASS | PASS (directions analogy) | N/A (1-step) |
| boxes_sketches | PASS | PASS | PASS (cardboard analogy) | N/A (1-step) |
| smart_charts | PASS | PASS | PASS (marble-jars analogy) | N/A (1-step) |

Every cell that was "N/A — no analogy library entry" in round 1 is now a
genuine PASS. Zero leakage/readability gate rejections logged across the
entire sweep (checked the server log directly, not just the API responses).

### Solved-state check (Finding 1), specifically

Confirmed live in the browser for both problem shapes light-check topics
come in:
- **1-step** (`shapes_angles`, "Classify a 30° angle"): submitting the
  correct answer ("acute") immediately shows "Solved! Great work." — no
  phantom `Step 2` box.
- **2-step** (`patterns`, "2, 4, 6, 8, ..."): submitting both steps in order
  ("2", then "10") shows "Solved! Great work." after the second step, with
  both locked step boxes shown and no further input box.

### New findings this round

**None outstanding.** The two analogy/leakage collisions found while
implementing Finding 2 (`shapes_angles` naming its own answer vocabulary,
`symmetry`'s "nothing"/"no" substring collision) were caught and fixed
within this same round, before they reached a "found but deferred" state —
recorded above under Finding 2, not as new backlog items, since they were
side effects of Finding 2's own fix, not independently-discovered problems.
A permanent regression test now guards against a future analogy edit
reintroducing this same class of bug for any light-check topic.

### Verification

419 backend tests passing (12 new: 6 for the analogy library + collision
regression, 3 for mock's topic/hint_level variation, plus the existing
light-check/orchestrator suites unaffected), ruff/mypy clean; frontend
`tsc`/`eslint`/`vitest` clean. Confirmed live: the full 14-topic sweep, the
`shapes_angles`/`patterns` solved-state screenshots, and the
`shapes_angles` analogy-switch screenshot (both before the collision fix,
showing the bug, and after, showing it resolved).
