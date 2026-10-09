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
