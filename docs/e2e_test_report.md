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
