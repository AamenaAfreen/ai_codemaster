# Codenames LLM Study — Consolidated Findings

Master summary of what the 36-combo dataset (1,765 games, GPT-4o-mini + Gemini 2.5
Flash Lite) shows. Self-Refine specifics live in `findings_directionality.md`; this is
the whole-project picture. Scripts: `analyze_project_overview.py`, `analyze_conservatism.py`,
`analyze_verifiability_flip.py`.

## F1 — The Guesser, not the Codemaster, controls the outcome
Guesser strategy marginal spread **41.7 pts** (Cautious 69% vs Self-Refine 28%,
chi-square=101, p<0.001). Codemaster spread **16.6 pts** pooled (chi-square=13.5) —
but ~10 pts on OpenAI alone; the pooled figure is inflated by Gemini's broken COT
codemaster. Either way the Guesser effect is several times larger. The original paper
fixed the Guesser at Default and so structurally could not see this.

## F2 — Teams essentially only lose one way: the assassin
**97% (OpenAI) / 98% (Gemini) of all losses are assassin deaths.** Blue-out and timeout
together are 2-3%. Across every strategy, Codenames-with-LLMs is an assassin-avoidance
problem. This single fact reframes the whole game and underlies F3-F5.

## F3 — "Conservatism wins" is too simple; it's avoidance via exposure AND accuracy
Guesses-per-turn alone barely predicts winning: corr(guesses/turn, win%) = -0.12.
Two distinct roads to the assassin:
- **Over-aggression** — Risky guesses 1.76 words/turn -> 47% assassin.
- **Inaccuracy** — Self-Refine guesses only 1.24/turn yet dies most (72%) because its
  picks are wrong over many turns.
Cautious wins (69%) by avoiding both: one accurate guess per turn.
(Note: corr(assassin%, win%) = -1.00 is near-tautological given F2; not a standalone finding.)

## F4 — Real synergies exist between roles (invisible to a symmetric-pairs study)
Cell win rate vs the additive prediction from the two marginals:
- **Cautious Codemaster + Self-Refine Guesser: +15 (OpenAI), +27 (Gemini)** — a careful
  clue-giver disproportionately *rescues the worst guesser*. Consistent across providers.
- **COT Codemaster + Cautious Guesser: +10** — the 96% best combo is genuine synergy,
  not just two strong marginals stacking.
- Antagonism: double Self-Refine (-10); a Default Codemaster *underserves* the strong
  Cautious guesser (-11).
The original study only ran symmetric pairs and could not observe any of this.

## F5 — Reflection is double-edged; cost rarely justifies it
- **The Self-Refine flip (controlled in a 2x2):** the same self-critique step helps the
  informed Codemaster (+10 pts to add it) and hurts the uninformed Guesser (+40 pts to
  remove it) — opposite signs, decided by information access. The downside of uninformed
  critique is ~4x the upside of informed critique. Mechanism: the critique only adds value
  when it has NEW information to act on (CM sees the key; Guesser does not), not on wording
  (grounded-critique null: verifiable = fixed). See `findings_directionality.md`.
- **Cost-effectiveness (win per minute, OpenAI guesser):** Solo Performance 100, Default 65,
  Cautious 15, COT 8, Self-Refine 4. Multi-step strategies are slow and, except where they
  add real information, not worth the cost. Cautious is most accurate (82%) but slowest
  (forces 1 guess/turn -> more turns).

## Through-line for a standalone paper
"What governs success in cooperative LLM teams?" Answer from this data:
1. the uninformed agent is the bottleneck (F1);
2. because the task reduces to avoiding one catastrophic action (F2);
3. which is won by exposure control + accuracy, not cleverness (F3);
4. role pairings interact, so asymmetric tuning matters (F4);
5. and self-reflection helps only the agent that has information to reflect on (F5).
Self-Refine is the sharpest case study (F5), not the whole story.

## Open / next
- 2x2 (role x critique on/off) to convert F5's flip into a controlled causal claim.
- Multi-model robustness (Claude Haiku) on the ablation.
- Optional second-domain replication to promote F1-F5 from "Codenames" to "principle".
