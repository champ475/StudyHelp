# StudyHelp — Real-Time Mistake-Interruption Tutor for Class 5 Math
### Approach document (POC scope + research framing)

## 1. Restating the core idea

A tutoring system that watches a student solve a math problem step by step and interrupts at the exact step where a mistake is made — like a parent watching over a child's shoulder — rather than only checking the final answer. Instead of handing over the correct step, it diagnoses the specific misconception and guides the student to self-correct through Socratic dialogue.

POC constraints already set: class 5 math only, typed input only (handwriting OCR deferred), and — from your answers — **step-by-step submission** (student submits one step at a time, system checks before allowing the next step).

Step-by-step submission is the right starting choice for a POC. It gives you a hard boundary for "the moment of the mistake," which is exactly what continuous free-form typing can't reliably give you, and it removes an entire class of parsing ambiguity so you can focus research effort on detection quality and intervention design rather than on inferring where a step even begins or ends.

## 2. System architecture

**Problem representation.** Each problem is stored not just as a final answer but as an expected *step schema* — the sequence of valid intermediate states a correct solution passes through, plus the known alternate valid paths (there is often more than one correct way to solve a class 5 problem, and the system must not penalize a correct-but-unconventional method).

**Step verification, two layers:**

1. *Symbolic/rule-based layer* (deterministic). For arithmetic, fractions, decimals, LCM/HCF, and simple word problems, most steps can be checked with symbolic computation (e.g. sympy) or a small rule engine — is this step mathematically valid given the previous step, and does it move toward the goal. This layer is fast, free, and never hallucinates.
2. *LLM layer* (only invoked when the symbolic layer flags a step as wrong, or for step types the rule engine can't cover). The LLM's job here is not to decide right/wrong — the symbolic layer already did that — its job is to (a) classify the *type* of error and (b) generate the natural-language, age-appropriate Socratic explanation.

This two-layer split matters a lot for a system used by 10-year-olds: a pure-LLM checker can occasionally mis-grade a correct step as wrong or miss a real error, and for a young learner who has no way to sanity-check the tutor, an unreliable correction is worse than no correction. Grounding the verification in symbolic logic and reserving the LLM for language generation is both safer and cheaper to run at scale (an LLM call only fires on an actual error, not on every keystroke or every step).

**Error taxonomy.** Not every wrong step deserves the same response, and this is where the "mother teaching" framing actually becomes a design decision rather than a slogan. A useful primary-math taxonomy to start from:

- Careless/slip errors — transposition, sign flip, a copying mistake — the student knows the concept but executed sloppily. Response: a light nudge to re-check, not a re-teach.
- Procedural errors — a step of a known algorithm is skipped or done in the wrong order (e.g. forgetting to borrow, adding numerators and denominators directly). Response: point at the specific step of the procedure, walk through *why* it exists.
- Conceptual errors — the underlying idea is misunderstood (e.g. thinks a larger denominator means a larger fraction). Response: drop back to a concrete/visual re-explanation of the concept itself, then return to the problem.

Matching intervention style to error type (rather than giving one generic "here's what's wrong" for everything) is itself something worth evaluating empirically, not just assuming.

**Per-student knowledge model.** Log every step, error, error type, intervention given, and whether the student self-corrected after intervention. Over time this becomes a per-student misconception profile — useful both for adaptive problem selection later (scale-up feature) and as data for the research evaluation.

## 3. Research novelty — recommendation

You asked for a recommendation on where the gap is in AI-in-education. A few honest observations about the existing landscape:

- Classic intelligent tutoring systems (Cognitive Tutor, ASSISTments) and knowledge-tracing research are good at modeling *whether* a student has mastered a skill, but feedback is typically hint-on-demand or post-hoc, not a proactive interruption at the exact point of error.
- Recent LLM-tutoring work (Khanmigo-style products, Socratic-prompted LLM tutors, datasets like MathDial) explore dialogue-based tutoring, but much of it either waits for a full submitted (and often wrong) solution before engaging, or relies on the LLM itself to judge correctness — which is exactly the reliability gap noted above.

Given that, the framing I'd recommend for a paper is not "we built an LLM tutor" (that's crowded and not very novel on its own) but a controlled comparison that produces an actual empirical result:

**Core study: does interrupting at the point of error reduce repeated mistakes, compared to delayed/post-hoc feedback, for primary-school math learners?**

Three conditions, same students/problems where feasible:
- Immediate interruption (your system's core idea)
- Delayed feedback (student finishes the problem, then gets the same explanation)
- No intervention / plain right-or-wrong marking (control)

Outcome measures: rate of the *same* error type recurring on subsequent problems, time-to-mastery of a skill, retention after a delay (e.g. a week later), and secondary measures like frustration/engagement if you can capture them (even simple ones like time-on-task or abandonment rate).

This is a genuinely useful contribution because "immediate corrective feedback is better" is a claim from general education psychology, but demonstrating it concretely with an AI system that can actually do reliable point-of-error detection at scale, specifically for young learners in math, is the gap — most existing systems can't reliably say "the mistake was on step 3, and here's what kind of mistake it was" in the first place. The two-layer detection architecture (section 2) is what makes this study possible to run safely and is worth presenting as the system contribution that enables the empirical one. The error-taxonomy-conditioned intervention (section 2) is a strong secondary contribution/ablation if time allows: does matching intervention style to error type outperform a generic explanation.

This framing also keeps you honest about "actually usable, not just for research" — the system you need to build to run this study *is* the deployable product; the study doesn't require a separate throwaway prototype.

One thing to flag now rather than later: this involves data collection from children under 18. Even for a POC/pilot, you'll want parental consent and likely school or institutional approval before running any study with real class 5 students, and anonymized data handling. Worth scoping this early since it affects timelines more than the engineering does.

## 4. Tech stack — recommendation

- **Backend:** Python (FastAPI) — plays well with both symbolic math (sympy) and LLM orchestration.
- **Symbolic verification:** sympy plus a small rule engine per problem type for the POC topic set. For arithmetic/fractions/decimals/LCM-HCF this covers the large majority of steps; word problems need a lightweight structured representation (quantities + operations) rather than full NLP parsing.
- **LLM:** used only for (a) classifying error subtype once the symbolic layer has flagged a step wrong, and (b) generating the Socratic, age-appropriate explanation. Keeping LLM calls conditional on a detected error (not per-step) keeps cost and latency low enough to actually scale to classroom use.
- **Frontend:** a structured step-input UI (not free LaTeX/handwriting) — a simple math-aware input component per step, matching the step-by-step submission model you picked. This avoids needing OCR or LaTeX parsing entirely, consistent with the POC's existing typing-only assumption.
- **Logging/data layer:** every step, verdict, error type, and intervention outcome stored for both the adaptive knowledge model and the research evaluation — this data is your paper's dataset, so schema it deliberately from day one rather than as an afterthought.

## 5. Suggested POC scope (superseded — see section 7)

- Pick 2–3 class-5 topics with well-documented, well-studied misconceptions in math-education literature (this matters for grounding your error taxonomy in real pedagogy rather than inventing categories from scratch) — e.g. multi-digit subtraction with borrowing, addition/subtraction of fractions with unlike denominators, LCM/HCF.
- Build the step schema + symbolic checker for just those topics.
- Build the minimal step-by-step input UI.
- Wire in the LLM for error classification + explanation generation, prompted for age-10-appropriate, warm, Socratic tone — explicitly not handing over the corrected step.
- Instrument logging from day one.
- Draft the three-condition study protocol and the consent/approval process in parallel with the build, since that will gate when you can actually run the evaluation.

## 6. Open questions (as of section 1–5, now mostly resolved — see section 7)

- Which 2–3 topics to start with, and whether you have access to real class 5 students/a school for the eventual study, or whether an initial pilot needs to run with a smaller informal group first.
- Whether the LLM-generated dialogue should be a single-turn explanation or a multi-turn back-and-forth (the "mother teaching" framing suggests multi-turn, but that's more complex to build and evaluate).
- How much of the adaptive/longitudinal misconception model to include in the POC vs. treat as a v2 scale-up feature.

## 7. Evaluation of your latest decisions

You asked not to just be agreed with, so here's an honest read on each of the four calls you made, including one place I'd push back.

### NCERT Class 5 CBSE textbook as source of truth — agree, no real downside

This is a good anchor decision. It gives you a bounded, well-defined syllabus, a defensible "source of truth" for problem generation and step schemas, and it's easy to justify in a paper ("aligned to the NCERT Class 5 curriculum" is a concrete, checkable scope statement). One implication worth planning for now rather than discovering later: not every NCERT Class 5 chapter fits the step-by-step-typed-solving interaction model equally well. Arithmetic, fractions, decimals, LCM/HCF, and most word problems decompose naturally into checkable steps. Chapters like Data Handling (pictographs/bar graphs), Patterns, and parts of Geometry (shape/symmetry recognition, angle identification) are much more about recognition or construction than a linear sequence of algebraic steps — there isn't always an obvious "step 3" to interrupt at. Worth doing a quick chapter-by-chapter audit early: which chapters map cleanly to step-verification, which need a different interaction pattern (e.g. a diagnostic question rather than a worked step), and which might just get a lighter-weight treatment (final-answer-only checking) in v1 even though the syllabus technically includes them.

### Multi-turn dialogue — agree it fits the framing better than single-turn, but it raises the engineering and evaluation bar

Multi-turn is the right call if the "mother teaching" framing is meant literally — a real correction usually isn't one message, it's a back-and-forth until the child actually gets it. But a few things to plan for deliberately rather than let emerge:

- **State management.** You now need per-step conversation state (not just per-problem), and a way to know when a turn has "succeeded" (student demonstrates understanding and correctly redoes the step) versus needs another turn.
- **A turn cap with a graceful fallback.** Open-ended multi-turn dialogue with a 10-year-old risks a frustration loop if the child still doesn't get it after several tries. Decide up front what happens after N turns — e.g. show a fully worked example and let them proceed, rather than trapping the student in an unresolved dialogue.
- **Evaluation gets harder.** Single-turn explanation quality is easy to rate with a rubric. Multi-turn dialogue quality is a genuinely harder eval problem — you'll want a concrete success metric such as "did the student produce a correct step within N turns" rather than relying on subjective dialogue-quality ratings alone, both for iterating on the system and for the eventual paper.
- **Grounding doesn't stop after turn 1.** The two-layer verification idea (section 2) mostly protects the *first* correction. If the dialogue continues for multiple turns, later LLM turns are drifting further from the deterministic layer's grounding. Worth deciding whether later turns still get re-checked against the symbolic layer (e.g. when the student proposes a redo of the step) or whether the LLM is trusted to free-run the rest of the conversation.

### Building end-to-end for all of Class 5 math in v1 — this is the one I'd push back on

I'd separate "the architecture should be general enough to cover all of Class 5 math and beyond" (agree, build it that way) from "the first working version should have every topic implemented" (disagree, this is a scope risk). A few reasons:

1. Symbolic/rule-based verification effort is not uniform across topics. Arithmetic, fractions, decimals, and LCM/HCF are cheap to verify. Geometry, data handling, and patterns are each a distinct, non-trivial verification problem in their own right (visual/spatial reasoning, graph reading, sequence recognition) — building all of these before you have anything demoable pushes your first real interruption-in-the-moment demo, and your first usable data, much later than it needs to be.
2. For the research study specifically, coverage breadth actively works against you. A study needs enough *repeated observations per error type per student* to get statistical power. Spreading limited pilot students thinly across the entire syllabus gives you shallow data on everything rather than enough depth on anything — narrower topic coverage with more repetitions is usually the better research design choice, independent of engineering effort.
3. "Built end-to-end for Class 5 math" as a product claim and "architecture is topic-agnostic and designed to extend to the full syllabus, current release covers N of M chapters" as an engineering reality aren't in conflict — you can build the pipeline (step schema format, verification interface, error taxonomy, dialogue engine, logging) so that adding a new topic means writing a new verifier module against a stable interface, not re-architecting. That gets you the scalability story you want without gating v1 on full syllabus coverage.

My recommendation: treat "full Class 5 syllabus, same architecture, extends to other classes/subjects later" as the architectural target (design every interface with that in mind), but sequence topic coverage — ship a first slice (the 3–5 topics most cleanly suited to step verification and richest in documented misconceptions), get it in front of real students, then expand chapter by chapter within v1 using the same pipeline. This is a scheduling/sequencing disagreement, not an architecture disagreement — happy to go the other way if you have a hard reason v1 needs full coverage on day one (e.g. a pilot commitment tied to a full-syllabus product).

### Curated misconception reference file as LLM context — good idea, worth refining before building

The core idea is sound and I'd keep it — a curated bank of (misconception → likely mindset → example explanation) grounds the LLM in real pedagogy instead of letting it improvise explanations for young children, and it doubles as a citable research artifact in its own right (a Class-5-aligned, NCERT-mapped misconception taxonomy is the kind of thing that gets referenced independently of the tutoring system, similar to how error/dialogue datasets get published alongside tutoring papers). Three refinements I'd make before implementation:

1. **Don't stuff the whole file into every prompt — retrieve, don't dump.** As the bank grows across topics, putting the entire file in every system prompt gets expensive and, more importantly, dilutes the LLM's attention across mostly-irrelevant entries when only one or two are relevant to the current error. Better to key the bank by topic + error type (tying it directly to the taxonomy in section 2) and retrieve just the matching entries for the detected error — a light lookup, not full RAG infrastructure needed at this scale.
2. **Treat the one-shot example as a strategy to adapt, not a template to copy.** A worked example risks the LLM reproducing it near-verbatim instead of tailoring the explanation to the actual numbers and context of the student's specific problem. Prompt it explicitly to use the example as a demonstration of *approach and tone*, not as text to reuse, or the multi-turn dialogue will feel canned across different students working on different numbers.
3. **Decide the sourcing process for the bank itself, and treat it as a living document.** A manually curated seed list grounded in actual primary-math-education literature and NCERT teacher resources gives you research credibility from the start; real logged errors from pilot use should then feed back into enriching and correcting the bank over time. Worth deciding now who curates the seed list and what the update process looks like once real student data starts coming in — this bank is a first-class project artifact, not a one-time text file.
