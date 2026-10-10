# Roadmap — staged work and registered triggers

Status legend: **done** · **in flight** · **staged** · **registered
trigger** (gated — built only if the evidence demands it).

## Current release (v0.1, research preview)

- [x] Verbatim log of record; sentence corpus + stemmed inverted
      index retrieval with typed absence
- [x] Canonical fact tier with utility-density presentation wall,
      probationary admission, wall-as-rehearsal semantics
- [x] Ghost ledger with eviction provenance and probe-time recovery
- [x] Meta-namespace: schema-gated operational lessons, persisted
      cross-run, applied at probe time
- [x] Verdict taxonomy (MISS / CONFABULATE / ADJACENT /
      ABSTAIN-PLUS / HIT / INVALID-RUN) with decline-wins scoring,
      normalization, stoplists, and correction detection
- [x] Seal-checked, hash-chained compaction with pre-sweep
      verification
- [x] Scenario-as-data interface (JSON scenarios; a variant
      scenario proven first-contact)
- [x] Evidence: transfer matrix, SDT decomposition, fabrication
      floor (4 configurations), falsifier scorecards

## Next (in flight or staged)

- **Cross-model evaluation** — in flight: a second reader
  (12B-class) on the identical battery + log + lessons. This is
  the portability claim's primary test.
- **Scenario generator** — staged: template-based generation of
  scenario variants (new names, values, paraphrased turns) to
  measure the fabrication floor across domains, not just one
  fiction.
- **Packaging refactor** — staged: the research harness becomes a
  library (store, index, retrieval, scorer, meta as importable
  modules); scenarios and reader config as data.
- **Conformal threshold calibration** — staged (M2): the typed-
  absence threshold calibrated on the miss set instead of
  hand-picked, with a coverage certificate.
- **BM25 retrieval scorer** — staged (M4): drop-in above the
  overlap counter.
- **Full-answer archiving** — staged (v19): store untruncated
  answers in probe records (display truncates, archive doesn't).
  Kills the ans[:200] approximation caveat hanging over every
  offline rescore. Backward compatible (old reports keep :200).
- **Serial-position wall order** — staged experiment: highest-
  density items in FIRST and LAST wall slots (lost-in-the-
  middle applied to our own wall — the mid-wall is where
  attention is worst and where the v14 burial happened).
  Five-line build_wall change; predicts a small recall gain on
  mid-list facts.
- **Config user/internal split** — staged (release surface):
  explicitly split user-facing controls (reader, scenario, mode)
  from internal constants, after the toolkit-audit pattern.
  Parked, not staged: live loop-abort in generation (would
  violate the fixed-budget comparability contract; scoring-side
  gates stay the instrument).

## Registered triggers (gated — built only if evidence demands)

- **Learned relevance function (encoder)**: fires only if lexical
  retrieval provably underfits — misses where question and correct
  record share no lexical overlap, after the BM25 upgrade. If it
  fires: text-pair → score contract, version/domain/reader
  stamped, re-fit (not rebuilt) per domain.
- **Semantic-entropy probe**: fires if single-direction failure
  analysis is insufficient for the disposition measurement. The
  supervised descendant of our paired ablation study.

## Direction (the long arc)

Afterimage is the memory core of a larger hybrid thesis: the
deterministic layer provides guarantees that weights cannot
(exact retrieval, provenance, typed absence with certificates,
integrity chains), the trained layer provides what rules cannot
(generalization, composition, judgment), and the measured line
between them — what each side can and cannot be trusted to do —
is the actual research contribution. The fabrication floor is
that line, measured; a decoder trained with the absent-content
decline objective is the intervention that moves it; and this
repo ships the eval that proves whether it moved.

## What would make us wrong

- A read-path configuration that closes the fabrication floor
  without training (the memory system alone suffices — the
  two-layer thesis is wrong)
- Cross-reader evaluation showing the re-fit surface is larger
  than the portability contract claims
- A scenario class where the taxonomy fails to classify
  (unclassifiable failures = the eval is incomplete)

Each of these is a registered falsifier. Finding them would be a
result, and it would be published here.

---
**Michael Harding** — Afterimage. Deterministic memory for small models; measured before shipped.
