# Evidence — the measured results

Every number in this document was produced by the shipped eval
discipline: predictions registered before runs, scenarios as data,
deterministic greedy decoding, and a scoring taxonomy designed so
that honest failure and fabricated success are distinguishable.
Artifacts (transcripts, reports, score JSONs) are retained for
every run.

## The reader problem, measured first

Before any memory claim, the reader's raw behavior was measured —
because a memory system cannot be evaluated against a reader whose
honesty is unknown.

**CORRECTION (2026-10-09, strix 163):** earlier versions of this
document stated the fabrication-floor gap as
"reader-size-dependent." That attribution was confounded (n=2
readers differing in family, recipe, data, AND size) and is
withdrawn. The correct statement: the floor is READER-dependent;
size-invariance is UNTESTED (staged: same recipe, varying size).
The numbers below stand; the attribution changed.

### Fabrication floor on absent content

Across four read-path configurations, questions about *absent*
content (never-planted entities, attributes, and events —
genre-plausible so the test measures knowledge, not lexical
oddity):

    fabrication-or-leakage rate: 73-100%
    honest abstention rate:      0-11%

The floor is *scenario-independent* (confirmed on two different
scenario grounds) and *configuration-independent* (confirmed
across read-path variants). It is a reader disposition, and it is
the number any training objective must move.

### Discriminability (signal detection theory)

    d' = -0.03 to -4.4   (NEGATIVE across all configurations)
    c  = -0.20 to -1.50  (strongly liberal criterion)

d′ < 0 means the fabrication rate *exceeds* the recall rate: the
reader has no discriminability between known and absent — the
signal runs backwards. The criterion is liberal everywhere: the
reader would rather fabricate than decline.

**Consequence:** a memory system is evaluated on *delivery*
(does the right record reach the context), and the disposition
floor is the *training target's* acceptance number. The memory
system cannot fix what the SDT decomposition locates in the
reader — but it can deliver the evidence the reader needs, and
measure whether the reader uses it.

## The transfer matrix (memory system, measured)

Same store mechanics, same eval; the scenario surface and the
tuning state vary. Recall = planted-fact probes answered with the
expected token in the asserted answer segment.

| Ground | Run | Recall | Notes |
|---|---|---|---|
| Home | tuned | **18/21 (86%)** | high-water at home |
| New scenario, first contact | transfer | 16/21 (76%) | 2 owned harness bugs, fixed on the record |
| New scenario, tuned + lessons | recursion | **19/21 (90%)** | new ground, above home |
| Home, lessons applied | application | 18/21 (86%) | no regression with lessons active |
| Home, 12B reader (XT3) | cross-model | **18/21 (86%)** | cross-family, cross-size; recall transfers identically |

### T-series: belief revision (BADE) and supersession (v18)

The mutation (old mill → stone bridge) as a two-pass revision trial:
pass 1 reads the corpus *as of* the pre-mutation turn (time-aware
retrieval — the prior is real, not notional); pass 2 reads post-
mutation, plain and with a deterministic supersession line.

| Prediction (registered pre-run) | Outcome |
|---|---|
| B1: pass 1 establishes the prior | PRIOR-OK ("Old Mill") |
| B2: pass-2 plain revises | REVISED ("Stone Bridge") |
| B3: T2 note adds nothing (ceiling null) | confirmed — note/nonote identical, f9 NEW-OK both arms |
| B4: retention 17–19/21 | 18/21, rollback chain intact |

B1–B4 4/4. The reader revises on explicit disconfirmation; the T2
link's value on this scenario is architectural (auditable, grounded:
1 active, 0 dropped), not measured-revision. Miss disposition held
the 3B floor (8/14 dishonest). Side observation: f3 answered with
the mutation target ("Old Mill" for the lighthouse question) —
cross-fact leakage reaches into the f-series, not just the m-series.

### Weak disconfirmation (v18-weak): where T2 earns its keep

Same mechanics, hedged mutation ("might have burned… don't quote
me", both endpoints present, link grounded). Pass 2 reads the
identical context with and without the supersession line:

| Prediction (registered pre-run) | Outcome |
|---|---|
| W1: pass 1 establishes the prior | PRIOR-OK ("Old Mill") |
| W2: plain pass STICKS | STUCK ("Old Mill" — weak evidence insufficient) |
| W3: note arm REVISES (the money prediction) | REVISED ("Stone Bridge") |
| W4: retention 17–19 | 18, rollback intact |

W1–W4 4/4. The link's causal contribution is measured: STUCK →
REVISED on identical retrieval, the note line the only difference.
(Main f9 probe revised both arms — full-corpus retrieval already
surfaces the mutation strongly; the time-sliced BADE pair is the
clean ablation.) Miss floor 9/14. The T-series closes: T2 buys
auditability where evidence shouts, revision where it whispers.

### Temporal index (v19): the leak never mattered, the onset did

Corpus + index grow per lived turn (rebuild-per-turn,
parity-exact); early probes cannot see the future. Full-answer
archiving from this version (display truncates, never the record).

| Prediction (registered pre-run) | Outcome |
|---|---|
| R1: recall 15–18 (modest drop) | MISSED HIGH — 19/21. The registered alternative triggers: parity-plus means the future-leak never mattered for recall. Old numbers stand. |
| R2: early-cycle probes move most | inverted, better: f3 HIT at c2 (no old-mill lived yet) → MISS at c5/final (grab-source lived). Grab onset time-resolved. |
| R3: floor holds 7–10/14 | holds — 9/14 |
| R4: f9 NEW-OK holds | holds, both ablation arms |
| R5: within-probe fuel null | refined: recall covaries with n via grab-source presence (n proxies lived associates), not support count per se |

BADE held PRIOR-OK-REVISED both arms; S 7.21; rollback intact;
0 new lessons. Miss 4/1/5/3/1 (v2.4 live; v2.5 rescore pending
in the abstention baseline).

### Grab taxonomy (offline rescore, 26 frozen runs, zero new calls)

Historical f-MISS verdicts split into ABSENT vs GRABBED (answer
carries a different planted value). HIT counts untouched (380);
42 grabs recovered from the MISS pile:

| Prediction (registered pre-run) | Outcome |
|---|---|
| G1: grabs concentrate late | confirmed — final 0.36 vs cycle 0.24 |
| G2: mutation TARGET grabs most | FAILED — the OLD mill leads 22 (stone bridge: 1) |
| G3: f3/f8 grab most | half — f3 dominates (24), f8 nearly never (1) |
| G4: headlines stand | confirmed — GRAB splits MISS only |

Grab pairs: f3→old mill x21, f6→1214 x6, f9→lighthouse x3.
Mechanism, revised: grabs flow along ASSOCIATIVE lines
(rendezvous↔rendezvous, location↔location, same-turn neighbors
like f6/f7 sharing plant-3) and follow FREQUENCY, not recency —
the old mill co-occurs with "rendezvous" in two turns to the new
value's one. The reader reaches for the most-associated filler,
not the newest. Spec: grab_rescore_v1.json (42 rows).
Prior-sampling, cleanest case (v19 side-datum): m05 invents a
THIRD distinct name for the same absent slot across runs
(Florence / Mary Anning / Emily) — fabrication samples priors
per-run, it does not retrieve them. Pair-building corollary:
absent-slot confabs are UNSTABLE labels; pairs use the DECLINE
as chosen (stable) with the confab side representative-only.

### Runtime answer gate (lie detection as a rung)

The taxonomy ports to serving time without gold lists: every
SPECIFIC asserted in the answer segment (numbers, capitalized
names) must occur in the retrieved context (normalized). No
specifics = vacuous PASS (assertions flagged, absences never).
Measured on banked v18/v19 probes against full retrieved ctx:
HIT pass **53/55 (0.964)**, CONFABULATE flag **15/15 (1.000)**.
(Against truncated ctx the same gate collapses to 0.164 --
context fidelity is load-bearing, stated.) Residual: enumerated
answers ("1. Blue moss") handled by stripping list markers.
Limits, stated: closed-world only (power = store coverage);
adversarial paraphrase past normalization escapes it; revision
loop (re-prompt on FLAG) staged -- BADE measured the reader's
revision propensity (B2/W3), the loop itself unbuilt.
`gate_answer()` in the library, tested.

### Cross-model disposition (XT3, v2.3-corrected)

Same 18/21 recall — but the miss channel splits by reader:

| Reader | Dishonest | d′ | c |
|---|---|---|---|---|
| Qwen2.5-3B | 8–9/14 (~64%) | ≈ −0.6 | ≈ −1.0 |
| Gemma4-12B-SFT | 3/14 (21%) | ≈ +1.6 | ≈ −0.27 |
| Gemma4-12B-λ0.7 | 5/14 (36%) | ≈ +1.2 | ≈ −0.5 |

The λ point sits between full-SFT and base on every disposition
axis: recall untouched, fabrication 21% → 36%, d′ +1.6 → +1.2.
**Disposition is partially task-vector-representable** — and the
price of math recovery is now on the table instead of guessed.
The remaining 12B fabrications are all adjacency-grabs (near-real
values); pure invention is zero.

### The λ operating point (knowledge battery, 468 probes)

| Arm | Math | Unknown-entities | Reading |
|---|---|---|---|
| Raw obliterated base | 0.38 | 0.163 | math intact, entities refused |
| +30k fantasy SFT | 0.24 | 0.271 | entities bought with math |
| +λ0.7 dial | **0.36** | **0.264** | 95% of base math, 96% of SFT entity gain |

The dial is Pareto-dominant over both endpoints for this trade:
math recovers 0.24 → 0.36 while entities hold 0.271 → 0.264.
Flip analysis (0/10 gold-anywhere) rules out format drift as the
mechanism. Sources: `unified_xtx_arms_base_control.json`,
`unified_xtx_arms_30000.json`, `unified_lambda_knob.json`.

### Domain-hole battery (ablation holes, mapped not assumed)

52 ground-truth probes across 7 domain families (chemistry,
medicine, law, sciences, psychology, violence-handling,
NSFW-coherence), scored by exact-token match after ordinal+stem
normalization. Run to test whether predicted ablation holes exist
as *knowledge* gaps:

| Arm | Total | Notes |
|---|---|---|
| Raw obliterated base | 47/52 (90%) | no craters on any family |
| +30k fantasy SFT | 48/52 (92%) | +1 medicine row recovered |
| +λ0.7 dial | 49/52 (94%) | +1 violence-handling row |

No family scores below 6/8 on any arm. The predicted holes do
not exist as knowledge gaps — the ablation damage is behavioral
(disposition), not informational. Training and the dial fill
rows; neither creates craters. Spec: hole_map_v1.json (52 rows).

The failure taxonomy across all runs: every miss classified —
attribute binding, morphological key gaps, cross-fact leakage
(ADJACENT), semantic invention (CONFABULATE), honest decline
(MISS). No unclassified failures remain.

## The falsifier scorecards

Predictions registered before each run; verdicts on the record.

### Cross-model transfer (XT3, 12B reader on Qwen-built data)
Same scenario, same questions, Gemma4-12B-SFT reader instead of
the Qwen2.5-3B home reader. No per-reader tuning: the identical
instrument.

| Metric | 3B reader (v16.1b) | 12B reader (XT3) |
|---|---|---|
| Recall (planted facts) | 18/21 (86%) | **18/21 (86%)** |
| Fabrication on absent content | ~73% | **~21%** |
| d′ (discriminability) | ≈ −0.6 | **≈ +1.6** |
| criterion c | ≈ −1.0 (liberal) | ≈ −0.27 (near-neutral) |
| Pure inventions | present (Emily, 1955) | **zero** (all failures adjacency) |

Recall transfers identically; disposition does not — the bigger,
aligned reader declines honestly where the small one fabricates.
The fabrication floor is reader-dependent, and the instruments
measure it per reader in two numbers.

The three XT3 misses are all the same f3 interference ("old
mill" asserted for the primary rendezvous) — cross-fact
retrieval interference that is READER-INDEPENDENT. The split is
clean: interference lives in the store layer, fabrication in the
reader. One is ours to fix; the other belongs to training.

**Structural decay (fragment collapse under repeated
compaction):** predicted structurally dead once extraction was
restricted to verbatim sources; confirmed — no fragment growth
across cycles on new ground.

**Adjacency mechanism:** predicted that plausible-wrong answers
would resolve to the *nearest real record* (digit rearrangements,
location grabs); CONFIRMED — measured at Jaccard 0.0
(token-identical grabs) versus ~1.0 for pure invention
(bimodal, gap-between-thresholds).

**Cross-scenario lesson transfer:** predicted that class-level
lessons (absence warnings, attribute hints) fire on new ground
while instance-level lessons (home-ground values) do not
false-fire; CONFIRMED — absence lessons fired 3/3 on their
classes with zero false fires from home-ground values.

**Wall noise hypothesis** (fabrication is triggered by
distractor-rich context): the tuned run *disconfirmed* it —
fabrication persisted at typed-absence contexts with nothing
present. Reported negative, on the record: the fabrication floor
is prior-driven, and the fix is a training objective, not more
memory machinery.

## What the memory system changed, and what it cannot

**Changed (measured):** recall on planted facts 43% → 86–90%
across the harness generations; every failure classified; evictions
recoverable; absence typed; lessons persistent and applied.

**Not changed (measured, four configurations):** the fabrication
floor on absent content. This is the honest boundary of a memory
system: delivery is guaranteed, disposition is not. The floor is
the acceptance number for a *training* objective (the absent-content
decline behavior in the decoder's training data), and the eval
suite ships for exactly that measurement.

## Methods (so it can be reproduced)

- Greedy decoding throughout; predictions registered before runs
- Scenarios as JSON data files (facts, probe keys, turns, miss
  rows as pattern keys, planted inventories)
- Scoring: regex keys with word boundaries, decline-wins
  precedence, planted-value/name stoplists, correction detection,
  ordinal+stem normalization; assertion-segment scoring (context
  regurgitation is not recall)
- Probe taxonomy: MISS (absent, declined), CONFABULATE (asserted
  invented content), ADJACENT (asserted a near/leaked real
  value), ABSTAIN-PLUS (corrected), HIT (planted, asserted),
  INVALID-RUN (anchor failure)
- All transcripts, verdicts, retrieval counts, and report JSONs
  retained per run

---
**Michael Harding** — Afterimage. Deterministic memory for small models; measured before shipped.
