# Finding: the Self-Refine assassin failure is *volume-driven*, not *directional*

**Date:** 2026-06 · **Status:** internal, pre-Markus · **Script:** `analyze_assassin_directionality.py`

## TL;DR
Our prior narrative — *"the buggy critique made the guesser actively pick the
assassin"* — is **not supported by the aggregate per-game logs**. When the
Self-Refine guesser makes a mistake, it lands on the assassin at essentially the
chance rate. Its catastrophic assassin-death rate is explained by the *sheer number*
of wrong guesses it makes, not by an attraction toward the assassin specifically.

## Evidence (pooled OpenAI+Gemini per-game logs)

**Metric B — conditional on making a mistake, did the error hit the assassin more
than uniform chance over non-red words?** (the confound-controlled test)

| Guesser | Errors | AssnErr | Actual% | ExpUnif% | Ratio |
|---|--:|--:|--:|--:|--:|
| Default | 2140 | 181 | 8.5% | 7.6% | 1.11x |
| Cautious | 1562 | 113 | 7.2% | 7.8% | 0.93x |
| Risky | 2070 | 160 | 7.7% | 7.7% | 1.01x |
| COT | 1597 | 142 | 8.9% | 7.3% | 1.21x |
| **Self Refine** | **4585** | **413** | **9.0%** | **9.1%** | **0.99x** |
| Solo Performance | 2112 | 188 | 8.9% | 7.6% | 1.17x |
| Three Step | 520 | 46 | 8.8% | 7.4% | 1.19x |

Self-Refine sits at **0.99x** — no assassin-specific pull. Several *other* strategies
show *more* directional pull (COT 1.21x, Solo 1.17x). What sets Self-Refine apart is
the **error count: ~8 wrong guesses per game vs ~4–5 for the others** — it roughly
doubles total mistakes, and at a chance assassin rate that volume produces frequent
instant losses.

## Why this is actually a *stronger*, more defensible story
It aligns with Huang et al. (ICLR 2024), *"LLMs Cannot Self-Correct Reasoning Yet"*:
an unverifiable self-critique step adds **noise**, broadly degrading guess quality. In
a game with an instant-loss tile, broad degradation cashes out as frequent catastrophic
loss. The mechanism is *quality collapse via uninformed refinement*, not *assassin
attraction*.

## Caveats / what this does NOT yet settle
- The logs **pool** buggy-era and fixed-era critique runs; the on-disk data can't be
  cleanly split by the fix commit (the fix-rerun commit only rewrote the aggregate JSON
  and docs, not the per-game logs or the prompt file). So a directional effect unique to
  the *buggy* prompt could be diluted here.
- Per-game logs have **no provider label** → OpenAI/Gemini are pooled.
- These logs contain **no reasoning traces** → we cannot see the critique's reasoning.

## Decisive next test (instrumented, run-ready)
`run_selfrefine_ab.py` runs the **buggy vs fixed** critique on the *same* seeds with
**full trace capture** (validated end-to-end in mock). It directly answers:
1. Does the buggy prompt raise the assassin-death rate vs the fix? (re-confirm)
2. Does it produce assassin-specific directionality (Metric B > 1) that the fix removes?
3. Traces let us *read* whether the model reasons "this might be the assassin" → switches.

Toggle: `SELF_REFINE_CRITIQUE=buggy|fixed` (guesser_gpt.py). Needs API keys.

## UPDATE — controlled A/B with traces (run 2026-06, n=5/condition, Default CM)

Ran `run_selfrefine_ab.py` (buggy vs fixed critique, same seeds, traces captured) and
mined the critique step with `analyze_selfrefine_traces.py`.

Outcomes (small n, suggestive): buggy 0/5 wins, **5/5 assassin deaths**; fixed 1/5
wins, 3/5 assassin deaths.

Trace mechanism (160+ critique pairs, robust):

| critique outcome | buggy | fixed |
|---|--:|--:|
| changed the initial guess | 100% | 96% |
| → switched onto ASSASSIN | 6% (5) | 4% (3) |
| → RED→non-RED (destroyed a correct pick) | **65% (55)** | 61% (46) |
| → non-RED→RED (helpful) | 6% (5) | 12% (9) |

**Conclusion: not assassin attraction.** Onto-assassin switches are ~6% (buggy) vs
~4% (fixed) — barely different. The dominant effect is that the critique overrides the
guess ~100% of the time and converts a *correct* red pick into a *wrong* one ~two-thirds
of the time. The buggy prompt is worse because it helps half as often (6% vs 12%) and
harms slightly more, prolonging games until the assassin is hit at chance. This
*causally confirms* the volume / quality-collapse mechanism (aligns with Huang et al.).

Nuance to keep: in buggy losses the fatal assassin pick often came *via* a critique
switch (5 onto-assassin / 5 losses) — the critique is implicated in the fatal move, but
it is drawn to *changing answers*, not to the assassin specifically.

Caveat: n=5/condition, one codemaster. Scale to seeds=30 + a second codemaster (COT)
to firm up the outcome rates before any firm claim.

## FINAL — four-condition critique ablation (n=60/condition, Default+COT, OpenAI)

| condition | win% | assassin% | critique changed guess | correct→wrong | onto assassin |
|---|--:|--:|--:|--:|--:|
| **none** (no critique) | **73%** | **27%** | — (no critique) | — | — |
| verifiable (grounded) | 22% | 73% | 92% | 60% | 6% |
| fixed | 22% | 73% | 93% | 60% | 6% |
| buggy | 3% | 87% | 99% | 62% | 7% |

### The mechanism, settled
1. **The critique step itself is the failure.** Removing it (`none`) takes the worst
   guesser strategy from 22% to **73%** — comparable to the best (Cautious). The initial
   guess is good; refinement destroys it.
2. **It is NOT assassin attraction** (onto-assassin 6–7% across all variants, ~chance).
3. **It is NOT bad wording.** A *verifiable* critique grounded only in clue-association
   performs identically to `fixed` (22%/73%, same 60% correct-destruction). Rewording the
   critique does nothing.

### The governing variable: does the critique have NEW information?
The verifiability-of-the-question hypothesis is refuted. The real variable is whether the
critique step can draw on information the first pass lacked:
- **Codemaster** self-refine can consult the hidden key grid → genuine new signal →
  *helps* (+35 pt flip, both providers).
- **Guesser** self-refine has nothing new — clue-association is the SAME signal the initial
  guess already used — so any critique, however worded, just re-perturbs an already-good
  answer and overwrites correct picks ~60% of the time.

This is a clean two-role instantiation of Huang et al. (ICLR 2024): LLMs can't self-correct
without an external/new signal. Same model, same technique, opposite outcome by role.

### The standout paper thesis (defensible, evidence-backed)
"Self-critique helps an LLM agent only when the critique can draw on information the first
pass lacked. In a cooperative game we apply the same self-refine technique to two roles:
it improves the fully-informed Codemaster but collapses the uninformed Guesser (35-pt
swing). Traces show the Guesser's critique overrides 93% of guesses and flips correct→wrong
60% of the time; ablation shows removing it recovers performance (22%→73%); a grounded-
critique control shows rewording doesn't help — isolating *access to new information*, not
prompt phrasing, as the governing variable."

## 2x2 — controlled role x critique experiment (n=30/cell, Self-Refine both roles, OpenAI)

Win rate:

| | Guesser critique ON | Guesser critique OFF |
|---|--:|--:|
| CM critique ON | 37% | 63% |
| CM critique OFF | 13% | 67% |

Main effects: removing Guesser critique **+40 pts**; adding Codemaster critique **+10 pts net**.

**Controlled causal claim:** the same self-critique step has opposite signs by role —
strongly harmful to the uninformed Guesser (+40 to remove it), net helpful to the informed
Codemaster (+10 to add it). Same technique, opposite effect, decided by information access.

Honest refinements from the controlled design:
- The CM benefit is **interaction-dependent**: it rescues the worst cell (gON: 13%->37%)
  but does nothing when the guesser is already good (gOFF: 67% vs 63%, within noise).
- The earlier "+35 flip" (Self-Refine-as-CM vs Self-Refine-as-Guesser marginals) **conflated
  role with critique**. The clean 2x2 isolates the critique step: **+10 (CM) vs -40 (Guesser)**.
  The downside of uninformed critique is ~4x the upside of informed critique.

## Action items before/at Markus meeting
- **Stop asserting "it actively picks the assassin"** in talks/CV/LinkedIn until the A/B
  confirms it. Current safe claim: *"uninformed self-critique roughly doubles guessing
  errors, which in a game with an instant-loss tile produces frequent catastrophic loss."*
- Decide whether to run the A/B (cheap on gpt-4o-mini) to test the directional claim
  head-on with traces.
