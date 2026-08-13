# StudyHelp — Technical Architecture (Engineer's Deep Dive)

This is the engineering-level design for the system discussed so far: NCERT Class 5 CBSE math, typed step-by-step input, multi-turn Socratic dialogue, curated misconception bank, architecture general enough to extend to more classes/subjects later.

**Revision note:** this version incorporates seven concrete changes made after cross-checking the original design against the literature survey. They're marked inline with `[REVISED — <citation>]` where they change something from the original plan, and summarized with full citations in section 12 at the end. The short version: the LLM's role got *narrower* almost everywhere it appears (closed-set classification instead of open diagnosis, a mandatory decide-before-generate step, a deterministic leakage filter on every turn), because the literature is fairly consistent that LLMs are currently unreliable at exactly the two things the original design was implicitly trusting them with — localizing where an error occurred, and staying safely non-revealing over a multi-turn conversation.

## 0. Summary of what changed and why

| # | Original design | Gap found in literature | Change made |
|---|---|---|---|
| 1 | LLM fallback classifies novel errors directly into the taxonomy | LLMs score F1<0.5 diagnosing *why* a student erred (Jin et al. 2024, COLM), and are poor at exact error localization even with the right answer in hand (Srivatsa et al. 2025, EMNLP) | Classification becomes **closed-set, topic-constrained** (pick from retrieved candidates, don't freely diagnose) — see section 4 |
| 2 | Dialogue orchestrator generates a Socratic message directly from (error, misconception context) | Wang et al. 2024 (NAACL, "Bridge") found GPT-4 conditioned on an explicit diagnose→strategy→intent decision was preferred 76% more than unconditioned generation | Split every turn into a **decide step, then a generate step** — see section 6 |
| 3 | Turn-budget cap + one output-safety pass | SafeTutors (Hazra et al. 2026) found answer-over-disclosure harm rate rises from 17.7% to 77.8% across dialogue turns — multi-turn is specifically where LLM tutors degrade | Add a **deterministic, per-turn leakage filter** that checks the LLM's draft message against the known correct step/answer before it ever reaches the child — see section 6 |
| 4 | "Age-appropriate tone" as a prompt instruction | Parra et al. 2026 found LLM tutor responses need a *higher* reading level than human tutors by default; Jiao et al. 2025 found children over-trust AI even when it's wrong | Add a **measurable readability gate** (not just a prompt request) on generated messages — see section 6 |
| 5 | Error classification LLM call framed generically ("what's wrong with this step") | Song et al. 2026 named a specific failure mode: LLMs default to an "examinee" mindset (try to re-solve the problem) instead of a "diagnostician" mindset (explain why *this* answer is wrong) | Explicit **role-framing fix** in the classification prompt — see section 4 |
| 6 | Novel-error review queue triaged manually | Feldman et al. 2018 (CHI) demonstrated automatic clustering/synthesis of buggy rules from multiple student error instances is feasible | **Semi-automate** the review queue — cluster similar novel errors before a human reviews, don't review one-by-one — see section 4 |
| 7 | "Immediate interruption" implicitly treated as the obviously-correct default, with delayed/control only as study comparison arms | The timing-effect literature is genuinely unsettled — a 2026 meta-analysis (Kandemir et al., *Educational Psychology Review*) found *no* significant average effect of feedback timing in computer-assisted learning (g=0.03), and Metcalfe et al. 2009 found *delayed* feedback beat immediate for children specifically on a different task type; the productive-struggle literature (Young et al. 2024) explicitly hasn't resolved when to intervene | Intervention timing becomes a **first-class configurable policy** in the orchestrator, not a hardcoded default with study arms bolted on — see section 6 |

## 1. Overall shape of the system

```
Client (React web app)
   |  step submission, chat turns
   v
API layer (FastAPI)
   |
   +-- Curriculum Service        (problems, step schemas, NCERT chapter metadata)
   +-- Verification Service      (deterministic per-topic step checkers)
   +-- Error Classification      (buggy-rule matcher -> LLM fallback)
   +-- Misconception Bank        (structured KB, retrieval by topic+error signature)
   +-- Dialogue Orchestrator     (conversation state machine, LLM calls, structured output)
   +-- Student Model             (per-skill mastery, per-student misconception history)
   +-- Event/Analytics Log       (every step, verdict, turn, outcome — append-only)
   +-- Experiment Assignment     (condition per student/session, for the RCT)
```

Everything downstream of "student submitted a step" should be understood as a pipeline: **verify (deterministic) → classify (rule-first, LLM-fallback) → retrieve (misconception context) → converse (LLM, structured, turn-bounded) → re-verify on retry → log.** The LLM appears twice in this pipeline and never as the sole source of truth for correctness — that's the central design decision everything else follows from.

## 2. Problem & step-schema representation

Each problem is authored (not generated on the fly, at least for v1) against a formal schema, not just a final answer:

```json
{
  "problem_id": "subtraction-borrow-014",
  "ncert_ref": {"class": 5, "chapter": "Numbers and Operations", "topic": "subtraction_with_borrowing"},
  "given": {"minuend": 542, "subtrahend": 187},
  "step_graph": [
    {"step_id": "s1", "type": "align_place_values", "expected_state": {...}, "next": ["s2"]},
    {"step_id": "s2", "type": "subtract_units_with_borrow", "expected_state": {...}, "next": ["s3"]},
    ...
  ],
  "alt_paths": [...],
  "final_answer": 355
}
```

Key design choices here:

- **Step graph, not step list.** Class 5 problems very often have more than one legitimate path (different order of operations, different but valid intermediate groupings). A DAG of acceptable states, with a "did the student land on any acceptable next state" check, avoids the classic ITS failure mode of penalizing a correct-but-different method. `[REVISED — grounded further by Shih et al. 2023's own stated limitation]`: their deployed fractions ITS explicitly couldn't capture "all possible patterns of learners' responses" because it matched against a fixed pattern library rather than checking against any node in a full graph — real evidence this exact failure mode bites in practice, not just a theoretical concern. The verifier (section 3) should check the student's step against *every* reachable node in the graph, not just the immediate expected successor, and treat "matches a non-adjacent-but-valid node" as correct-but-flag-for-review rather than either accepting silently or rejecting.
- **Step type is a first-class field**, not inferred. This is what lets the verifier and the misconception bank be keyed consistently — "subtract_units_with_borrow" is both a node in the step graph and a lookup key into the misconception bank.
- **Structured student input, not free-text math parsing.** The single biggest tractability decision for the verifier layer: don't ask the student to type an arbitrary line of math and then parse it. Use a math-aware input widget (e.g. a MathQuill-style editor, or per-step-type structured fields — a borrow problem can have explicit "carry" and "digit written" fields) that emits an unambiguous structured value (a small JSON AST or a constrained LaTeX subset), not a raw string. This sidesteps an entire class of notation-ambiguity bugs (implicit multiplication, fraction-bar parsing, sign placement) that would otherwise eat a large fraction of engineering time for very little research value.
- **`[NEW — flagged by Shih et al. 2023]` Typing friction is a documented failure mode for this exact age group, not a hypothetical.** Their real deployment with 6th-graders explicitly reported that keyboard/mouse input was "time-consuming and inconvenient" for less tech-fluent children and caused impatience. Since the POC already accepts typed input as a prerequisite, the mitigation has to happen at the widget level: minimize keystrokes per step (numeric keypad, drag-to-place-digit interactions, tap-to-select from a small candidate set instead of typing a full expression wherever the step type allows it), and treat time-to-submit-a-step as a UX metric to watch during the pilot, not just an implementation detail.

## 3. Verification engine

A common interface every topic verifier implements:

```
verify_step(problem_state, student_step) -> {
  is_valid: bool,
  matched_step_id: str | None,
  confidence: float,
  error_signal: ErrorSignal | None   # structured, not free text
}
```

Under the hood, for arithmetic/fractions/decimals/LCM-HCF, this is largely sympy-backed symbolic equivalence checking (`sympy.simplify`, `.equals()`) plus a lightweight procedural state machine that knows legal transitions for that step type. For topics that don't reduce to symbolic manipulation (geometry construction, data-handling graph reading, pattern recognition), the same interface should still be implemented, but the backing logic is closer to a rule-based checker over structured input than symbolic algebra — the interface stays uniform even though the implementation differs a lot per topic, which is exactly what keeps "add a new topic" from becoming "redesign the pipeline."

**Bias toward false negatives over false positives.** If the verifier's confidence is low (ambiguous input, a plausible-but-unschemed alternate method), the system should default to *not* interrupting rather than risk wrongly telling a child they made a mistake. Wrongly accusing a correct answer of being wrong is more damaging to trust than occasionally missing a real error, especially for a young user who has no way to push back on the tutor. This should be an explicit, tested threshold, not an emergent behavior.

**This layer needs to be unit-tested like any deterministic software** — a golden set of (problem, injected wrong step) pairs per topic, run as regression tests. Since your research conclusions depend on the verifier being reliable, its test coverage is itself part of the research validity story, not just software hygiene.

**`[REVISED — Davis & Aaronson 2023]` The verifier must be a hard pipeline gate the orchestrator calls directly — never a tool the LLM is given and decides when/how to invoke.** This is a subtle but important distinction the original design left implicit. Davis & Aaronson's stress test of GPT-4 with WolframAlpha/Code-Interpreter plug-ins found the combined system was still unreliable largely because of "interface failures" — the LLM mis-formulating the query it sent to the tool, not the tool itself being wrong. If the LLM is ever in a position to decide whether to call the verifier, or to summarize/interpret the verifier's output before it reaches your orchestration logic, you've reintroduced exactly the failure mode the two-layer split was supposed to eliminate. Concretely: `verify_step()` runs automatically on every submission as regular application code, its structured result is what the orchestrator and dialogue-generation prompt consume, and the LLM is never handed a "check_step" function to call at its own discretion.

## 4. Error classification: buggy rules first, LLM as fallback

Worth grounding this in older but very relevant ITS research: the "buggy rules" tradition (Brown & Burton's DEBUGGY, VanLehn's repair theory) from the 1970s–80s showed that a large fraction of primary arithmetic errors are enumerable, systematic procedural bugs — not random noise. "Subtracts smaller digit from larger regardless of position" is a named, well-studied bug, not a one-off. This matters practically: a good chunk of your error classification can be done with a **library of pattern-matchable buggy rules** (given the student's wrong output and the correct one, does it match a known bug signature) before ever calling an LLM. This is cheap, deterministic, explainable, and — notably — gives you a genuine bridge between classic symbolic ITS research and modern LLM tutoring for the paper's framing, rather than positioning the work as "just another LLM wrapper."

Only when no buggy-rule signature matches does the LLM get invoked, and its role there is narrower than "grade this": given the correct step, the student's step, and the taxonomy (careless / procedural / conceptual), classify + produce a short structured rationale.

**`[REVISED — Otero, Druga & Lan 2025; Jin et al. 2024]` Make the LLM's classification job closed-set, not open-ended, and don't trust it unsupervised.** Two findings push a real change here. Otero et al. (2025) found GPT-4-turbo misconception-identification accuracy jump from 52.96% (unconstrained — pick from anything) to 73.82–83.91% (topic-constrained — pick from a scoped candidate set). Jin et al. (2024, COLM) found all 16 tested LLMs scored F1<0.5 diagnosing the cognitive cause of a math error, with strong *overconfidence specifically on wrong diagnoses* — meaning the failure mode isn't "the LLM says it's unsure," it's "the LLM is confidently wrong." Two concrete changes follow: (a) the classification call should be reframed from "what's wrong with this step" to a closed-set task — retrieve the candidate misconceptions for this `(topic, step_type)` from the bank first (section 5), and ask the LLM to pick the closest match or say "none of these," never to freely generate a new diagnosis in the same call; (b) because of the overconfidence problem, an LLM classification is never auto-trusted the way a buggy-rule-signature match is — it always gets a lower-confidence flag, and (per the point below) routes toward human review rather than being immediately promoted into the trusted taxonomy the dialogue generator relies on.

**`[REVISED — Song et al. 2026]` Fix the "examinee vs. diagnostician" framing explicitly in the prompt, don't assume it away.** Song et al.'s handwritten-math error-analysis study named a specific, reproducible LLM failure mode: when asked to explain a wrong answer, models default to an "examinee" mindset — quietly trying to solve the problem themselves and comparing to that — rather than a "diagnostician" mindset that reasons about why *this specific* answer is wrong given the *student's* (possibly flawed) approach. The classification prompt needs an explicit instruction countering this directly ("you are not solving this problem — the correct answer is given to you; your only job is to explain the specific reasoning path that would produce the student's incorrect answer"), and this should be a case in your eval set (section 9): does the classifier's stated reasoning path actually match the student's apparent approach, or does it just re-derive the correct answer and note a discrepancy.

**Every LLM-classified (i.e., novel/unmatched) error should be logged to a review queue.** `[REVISED — Feldman et al. 2018]` Rather than a human reviewing novel errors one at a time, semi-automate this the way Feldman et al.'s CHI 2018 system did — cluster structurally similar novel errors (same wrong-output pattern across different problems/students) before a human looks at the queue, so a reviewer confirms "this cluster of 12 similar errors is a new bug" once rather than triaging 12 near-duplicate items individually. Confirmed novel bugs get promoted into the buggy-rule library and the misconception bank. This closes the loop and is your data flywheel — the system gets cheaper and more deterministic over time as the LLM's job shrinks toward "explain," and the buggy-rule library becomes another citable artifact.

## 5. Misconception bank & retrieval

Structured table, not a flat text file, keyed for lookup:

| field | purpose |
|---|---|
| `id` | stable key |
| `topic` / `step_type` | ties to the step schema and buggy-rule signature |
| `bug_signature` | pattern used for rule-based matching, if applicable |
| `typical_mindset` | the misconception in plain language |
| `explanation_strategy` | the *approach* to correcting it, not a script to recite |
| `example_dialogue` | one-shot demonstration of tone/approach |
| `source` | literature reference or "logged + reviewed", for research credibility |
| `version` / `review_status` | curated seed vs. pilot-derived, reviewed vs. pending |

**Retrieve, don't dump.** `[REVISED — retrieval now happens earlier in the pipeline than originally scoped]` The original design had retrieval feed only the dialogue-generation call. Per the closed-set classification change in section 4, retrieval now needs to run *before* classification too — the candidate misconceptions for `(topic, step_type)` get pulled from the bank first, and the LLM classification call picks among them (or says "none of these") rather than diagnosing freely. So retrieval is invoked twice per error: once to constrain classification, once (with the now-confirmed single match) to ground dialogue generation. At call time, the dialogue orchestrator looks up only the entries matching the current `(topic, step_type, error_signature)` and injects those into the system prompt — not the whole bank. This keeps prompts small and keeps the LLM's attention on the one misconception that's actually relevant, which matters more as the bank grows across the full syllabus. No vector database is needed at this scale; a structured key lookup is simpler, cheaper, and easier to debug than semantic search. Embedding-based retrieval is worth revisiting later only if you start getting many *novel* errors that need matching to the "closest known" entry rather than an exact key match — a reasonable v2 addition, not a v1 requirement.

**The example is a strategy, not a script.** Prompt instructions should explicitly tell the LLM to use `example_dialogue` as a demonstration of tone and approach, and to generate its own explanation grounded in the actual numbers/context of the student's specific problem — otherwise you'll see near-verbatim reuse of the example across different students, which reads as canned and undermines the "understands this specific child's mistake" framing that's the whole point.

## 6. Dialogue orchestration (multi-turn, structured, bounded)

Model this explicitly as a state machine per (student, problem, step) instance:

```
ErrorDetected -> Explaining -> AwaitingRetry -> [Resolved | Explaining (next turn) | Escalated]
```

Concrete engineering decisions this implies:

- **Structured LLM output, not free prose parsing.** Use tool-calling / structured-output mode so each turn returns something like `{message: str, expects_retry: bool, hint_level: int, concept_flag: str|null}` rather than free text the orchestrator has to regex. This makes state transitions reliable and testable.
- **`[REVISED — Wang, Zhang, Robinson, Loeb & Demszky 2024, "Bridge", NAACL]` Split every turn into a decide step and a generate step — don't go straight from error to message.** This is the single highest-leverage change suggested by the whole survey. Bridge's controlled comparison found GPT-4 responses conditioned on an explicit expert decision framework (identify the specific error → select a remediation strategy → form instructional intent) were preferred 76% more than unconditioned responses, and — importantly — that *randomly assigned* decisions (i.e., going through the motions of a decision step without it being the right one) cut quality by 97% versus expert-informed decisions. So this isn't "add a planning step for its own sake" — the decision content has to actually be right, which is exactly why it's fed by the retrieved, topic-constrained misconception match from section 4/5 rather than invented fresh each turn. Concretely, each turn becomes two structured calls (or two phases of one call with an intermediate structured object): call 1 outputs `{error_type, remediation_strategy, instructional_intent}` grounded in the verifier's output and the retrieved misconception entry; call 2 generates the actual child-facing `message` conditioned on that decision object. This also makes the decision itself independently loggable and evaluable — you can check whether the *strategy chosen* was appropriate, separately from whether the *wording* was good.
- **Turn budget with graceful fallback.** Cap turns per step (e.g. 3–4). After the cap, don't leave the child stuck — show a fully worked example for that step and let them proceed, logging that this step "escalated" (itself a useful research signal — how often does the system fail to get the student there through dialogue alone).
- **Re-verification on every retry, not LLM self-assessment.** When the student resubmits a step mid-dialogue, that resubmission goes back through the deterministic Verification Service from section 3, not through the LLM's judgment of whether the student "seems to get it now." This is what keeps multi-turn dialogue from drifting away from the grounding that made single-turn correction reliable in the first place.
- **`[NEW — Hazra et al. 2026, "SafeTutors"]` A deterministic, per-turn answer-leakage filter, not just careful prompting.** SafeTutors' benchmark found pedagogical-harm rate (mostly premature answer disclosure) rose from 17.7% at turn 1 to 77.8% by later turns across every model they tested, and that "challenge" behavior — pushing the student toward their own reasoning rather than handing over the answer — was near zero across the board. Prompting alone ("don't reveal the answer") is evidently not sufficient once a dialogue runs several turns. Because StudyHelp already has the ground-truth correct step/answer from the schema (section 2), this is cheap to guard deterministically: before any generated message is sent to the child, string/value-match it against the known correct step and final answer (and close paraphrases/numeric matches), and reject-and-regenerate (with an explicit "don't state the answer" instruction appended) if it matches. This is strictly stronger than a generic moderation pass because it's checking against a known ground truth, not just vibes. `[Also relevant: Lee et al. 2026's "LeakShield" prompt-optimization technique — worth adopting as the first line of defense before the filter has to trigger a regeneration, since regeneration costs a turn from the child's limited budget.]`
- **Context scope, deliberately narrow.** Each LLM call gets: the problem, the specific step and student's specific wrong input, the retrieved misconception entry (not the whole bank), and the conversation history *for this step only* (not the full session) — this bounds context growth, keeps cost/latency predictable, and keeps the model from wandering off-topic across a long session.
- **`[REVISED — Parra, Corica & Godoy 2026; Jiao et al. 2025]` Age-appropriate language as a measured gate, not just a prompt instruction.** Parra et al. found LLM tutor responses require a *higher* reading level than human tutors' responses by default across every model they tested — the model doesn't self-correct for this without being forced to. Jiao et al.'s review adds a sharper reason this matters here specifically: children over-trust AI responses even when they're wrong, partly *because* of anthropomorphized, confident phrasing — so an over-complex or over-confident-sounding explanation isn't just harder to read, it's more likely to be blindly accepted even if subtly off. Concretely: run a cheap readability check (e.g. Flesch-Kincaid grade level) on every generated message against a target ceiling appropriate for a Class 5 reader, and regenerate with an explicit simplification instruction if it fails, the same way the leakage filter above works — a measurable gate, not a hope that "be age-appropriate" in the prompt is enough.
- **Streaming responses** in the UI — a 10-year-old's attention span makes a visible "thinking" spinner worse than for an adult user; stream tokens as they generate. (Note this now interacts with the two gates above: since messages may get rejected and regenerated by the leakage filter or readability gate, streaming should render only after a message has passed both checks, not stream the first draft speculatively.)
- **Defense in depth on output.** Even with careful prompting, run a lightweight content check on LLM output before it reaches the child (a cheap moderation pass), and have a canned fallback response ready if the LLM call errors or times out — never leave a child-facing UI with no response.
- **`[REVISED — Kandemir et al. 2026; Metcalfe, Kornell & Finn 2009; Young, Bevan & Sanders 2024]` Intervention timing is a configurable orchestrator policy, not a hardcoded "always interrupt immediately" default.** The original design treated immediate interruption as StudyHelp's obvious core behavior, with delayed/no-intervention only appearing as comparison arms for the eventual study. The feedback-timing literature doesn't support treating immediacy as the safe default this way: a 2026 meta-analysis specifically of computer-assisted learning (Kandemir et al.) found no significant average effect of timing at all (g=0.03) once heterogeneity is accounted for; Metcalfe et al. found *delayed* feedback outperformed immediate for children close to this age on a (declarative, not procedural) learning task; and the productive-struggle literature (Young et al. 2024) explicitly says the field hasn't resolved when outside intervention helps versus short-circuits useful struggle. Practically: the orchestrator should expose intervention timing as a policy parameter the pipeline consults per step — "interrupt on first error," "interrupt after Nth repeated error on the same step," "wait for problem completion" — rather than one behavior hardcoded into the state machine with alternates hacked in only for the study. This also directly simplifies running the three-condition study later, since conditions become policy configurations rather than special-cased code paths.

## 7. Student model / knowledge tracing

Track, per (student, skill/subskill): attempt count, error history by type, turns-to-resolution, and a mastery estimate. For v1, resist the pull toward a heavy model — a simple, explainable mastery score (a basic Bayesian Knowledge Tracing update, or even a decaying success-rate counter) is enough to support adaptive problem selection and is far easier to debug and explain in a paper than a deep-learning knowledge-tracing model trained on what will initially be a small amount of pilot data.

**`[REVISED — Pandey & Karypis 2019, "SAKT"]` If/when a v2 justifies a learned knowledge-tracing model, prefer an attention-based model over a plain LSTM (DKT), specifically because of the data regime StudyHelp will actually have.** The original doc named DKT/LSTM generically as the eventual upgrade path. Worth being more specific: SAKT was built to address exactly the weakness that matters here — RNN-based KT models need long interaction histories to work well, and a single Class-5 tutoring session is much shorter and sparser than the benchmark datasets (thousands of interactions per student) DKT was validated on. SAKT reported ~4.4% average AUC improvement over DKT-family baselines specifically on sparse-history data. This doesn't change the v1 recommendation (still skip deep KT entirely for now), but it changes what "v2" should reach for when the data volume argument is finally satisfied — attention-based, not recurrence-based.

## 8. Backend, data, and infra choices

- **API layer:** FastAPI — good ecosystem fit for both symbolic math (sympy) and LLM orchestration, async-friendly for streaming.
- **Primary datastore:** Postgres — problems, step schemas, misconception bank, buggy-rule library, users, sessions, event log all fit naturally as relational/JSONB data; no need for a specialized document or graph DB at this scale.
- **Session/dialogue-state cache:** Redis — active per-step conversation state needs fast read/write on every turn without round-tripping Postgres each time; Postgres remains the durable log.
- **Event logging:** an append-only events table (step submitted, verdict, error type, turn, resolution, escalation) is enough for v1; don't reach for a dedicated event store/warehouse (ClickHouse etc.) until actual query volume/pattern demands it — this is exactly the kind of infra that's easy to over-build before you have real usage to justify it.
- **LLM access:** Claude via API, structured/tool-output mode for the dialogue turns and error classification, with every call logged (prompt, response, latency, token cost) — needed both for debugging and because prompt/response pairs are part of your research artifact.
- **Experiment assignment, built in from day one:** condition (immediate / delayed / control) assigned and persisted per student or session in the same event schema, not bolted on later as a separate tracking system. Retrofitting an RCT's condition tracking after the fact is a common and avoidable source of pain.

## 9. Evaluation harness (engineering-level, distinct from the user study)

Two different kinds of evaluation, both needed:

1. **Deterministic regression tests on the verifier and buggy-rule matcher** — a golden set of (problem, injected error) pairs per topic, run in CI. This is standard software testing but worth calling out explicitly because your research conclusions are only as trustworthy as this layer's reliability.
2. **Dialogue quality evaluation** — harder, because it's generative. Track a concrete behavioral metric (did the student produce a correct retry within the turn budget) as the primary signal, supplemented by periodic rubric-based human rating (or LLM-as-judge, cross-checked against human rating on a sample) against the explicit tone/Socratic/no-answer-leakage constraints from section 6. Track this over prompt iterations so you can see whether changes actually improve outcomes rather than just changing style.
3. **`[NEW — follows from the section 6 revisions]` Three additional, narrower eval axes that the original two-part harness didn't separate out.** With the decide-then-generate split, strategy-selection quality can and should be evaluated independently of message wording — did the *decision* object (error type, remediation strategy, instructional intent) match what an expert reviewer would have picked, separately from whether the final phrasing was good (mirroring how Bridge itself evaluated decisions vs. generations separately). The leakage filter and readability gate both need their own regression test sets too — a set of known-leaky drafts that must be caught, and a set of over-complex drafts that must be caught — tracked as filter precision/recall over time, since a filter that's too aggressive will burn through the turn budget with pointless regenerations, and one that's too lax defeats its purpose.

## 10. Safety, privacy, and compliance — concrete, not just a caveat this time

Since this handles data from children under 18 in India, India's Digital Personal Data Protection Act, 2023 together with the DPDP Rules, 2025 is directly relevant — the Act treats users under 18 as "children" and the rules (notably around verifiable parental consent, Rule 10) impose specific requirements on consent and on tracking/behavioral-monitoring of children's data. This is not just a research-ethics footnote — it has direct implications for what you log (the per-student misconception/knowledge model is exactly the kind of behavioral tracking these rules are aimed at) and how you obtain and record consent before any real student's data is collected, even in a small pilot. I'd treat "get qualified legal guidance on DPDP compliance for this specific data model" as a concrete pre-pilot task, not something to defer — the requirements have consent-workflow implications for the product itself (e.g. a parental consent flow before a child's account can start generating logged data), which affects the build, not just the paperwork.

## 11. Concrete build sequence

1. Step-schema format + verifier interface finalized; misconception bank + buggy-rule library seeded for the first topic slice (schema/tooling work, no ML yet).
2. Verifier engine implemented for that slice, with the regression test set from section 9 passing before moving on.
3. Error classification (buggy-rule matcher + LLM fallback) wired to the verifier's output.
4. Dialogue orchestrator: state machine, structured LLM output, turn budget, re-verification on retry.
5. Frontend: structured step-input widget + streaming chat UI for the dialogue.
6. Logging/event infra + experiment condition assignment wired in before any real student touches the system.
7. Small real pilot on the first topic slice; review the novel-error queue; enrich the misconception bank and buggy-rule library from real data.
8. Expand topic coverage within v1 using the now-proven pipeline, prioritizing topics by how cleanly they fit the step-verification interaction model (per the chapter-by-chapter audit from the earlier discussion).

## 12. Full citations for this revision

All from `studyhelp_literature_survey.md`; repeated here with section references for traceability.

- Wang, Zhang, Robinson, Loeb & Demszky (2024). "Bridging the Novice-Expert Gap via Models of Decision-Making: A Case Study on Remediating Math Mistakes." NAACL 2024. [arXiv:2310.10648](https://arxiv.org/abs/2310.10648) — drives the section 6 decide-then-generate split.
- Hazra et al. (2026). "SafeTutors: Benchmarking Pedagogical Safety in AI Tutoring Systems." [arXiv:2603.17373](https://arxiv.org/html/2603.17373v1) — drives the section 6 per-turn leakage filter.
- Lee, Shin, Jeong et al. (2026). "LLMs Are Already Good Tutors: Training-Free Prompt Optimization for Pedagogical Math Tutoring." [arXiv:2605.27088](https://arxiv.org/abs/2605.27088) — "LeakShield" prompting technique, section 6.
- Parra, Corica & Godoy (2026). "Insights on the Pedagogical Abilities of AI-Powered Tutors in Math Dialogues." *Information* (MDPI), 17(1), 51. [link](https://www.mdpi.com/2078-2489/17/1/51) — drives the section 6 readability gate.
- Jiao, Afroogh, Chen, Murali, Atkinson & Dhurandhar (2025). "LLMs and Childhood Safety." [arXiv:2502.11242](https://arxiv.org/pdf/2502.11242) — supports the readability gate and the "children over-trust AI" rationale.
- Otero, Druga & Lan (2025). "A Benchmark for Math Misconceptions." *Discover Education*, 4, 277. [link](https://link.springer.com/article/10.1007/s44217-025-00742-w) — drives the section 4 closed-set classification change.
- Jin et al. (2024). "Investigating Large Language Models in Diagnosing Students' Cognitive Skills in Math Problem-Solving." COLM 2024. [arXiv:2504.00843](https://arxiv.org/html/2504.00843v1) — drives the "don't auto-trust LLM classification" change, section 4.
- Song et al. (2026). "Can MLLMs Read Students' Minds?" [arXiv:2603.24961](https://arxiv.org/abs/2603.24961) — drives the "examinee vs. diagnostician" prompt fix, section 4.
- Feldman, Cho, Ong, Gulwani, Popović & Andersen (2018). "Automatic Diagnosis of Students' Misconceptions in K-8 Mathematics." CHI 2018. [link](https://www.cs.cornell.edu/~molly/chi2018.pdf) — drives the semi-automated review-queue clustering, section 4.
- Shih, Chang, Kuo & Huang (2023). "Mathematics Intelligent Tutoring System for Learning Multiplication and Division of Fractions Based on Diagnostic Teaching." *Education and Information Technologies*, 28(7). [link](https://link.springer.com/article/10.1007/s10639-022-11553-z) — drives the DAG-matching fix and the input-friction UX note, section 2.
- Davis & Aaronson (2023). "Testing GPT-4 with Wolfram Alpha and Code Interpreter Plug-ins." [arXiv:2308.05713](https://arxiv.org/html/2308.05713v3) — drives the "verifier is a hard gate, not an LLM-invoked tool" rule, section 3.
- Kandemir, Esposito, Gurgand & Ramus (2026). "A Meta-Analysis of the Impact of Feedback Timing on Learning Outcomes in Computer-Assisted Learning." *Educational Psychology Review*, 38, Art. 13. [link](https://link.springer.com/article/10.1007/s10648-026-10117-8) — drives making intervention timing a configurable policy, section 6.
- Metcalfe, Kornell & Finn (2009). "Delayed Versus Immediate Feedback in Children's and Adults' Vocabulary Learning." *Memory & Cognition*, 37(8). [link](https://link.springer.com/article/10.3758/MC.37.8.1077) — same, section 6.
- Young, Bevan & Sanders (2024). "How Productive Is the Productive Struggle?" *International Journal of Education in Mathematics, Science, and Technology*, 12(2). [link](https://files.eric.ed.gov/fulltext/EJ1413403.pdf) — same, section 6.
- Pandey & Karypis (2019). "A Self-Attentive Model for Knowledge Tracing." EDM 2019. [arXiv:1907.06837](https://arxiv.org/abs/1907.06837) — drives the SAKT-over-DKT recommendation, section 7.

## 13. Sources for the DPDP compliance note (section 10)
- [India Data Privacy Laws: DPDP Act 2023 and DPDP Rules 2025 Complete Guide](https://www.recordinglaw.com/world-laws/world-data-privacy-laws/india-data-privacy-laws/)
- [Child Data Protection Under DPDP Act: Parental Consent Rules](https://ksandk.com/data-protection-and-data-privacy/child-data-protection-under-dpdp-act-parental-consent-rules/)
- [Rule 10 of Digital Personal Data Protection Act, 2023 — DPDP Rules 2025](https://www.dpdpa.com/dpdparules/rule10.html)
