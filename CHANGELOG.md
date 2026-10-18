# Changelog

All notable changes, newest first. Falsifier results included where
they exist - this log records what the instruments said, including
the negative results.

## [Unreleased]
- afterimage_decline module (vendored, stamped): validated decline
  detection from the crucible refusal/abstention program, ported
  after measuring the gap on 6,113 real reader outputs -- 8/21
  DEFAULT_DECLINE_MARKERS dead, and the vocabulary misses 67% of
  canonical declines (the missed class is grounding-based: "I
  cannot see", "I can't tell you what you dreamed"). ADDITIVE only:
  miss_verdict's scoring order and DEFAULT_DECLINE_MARKERS are
  unchanged; the module ships classify_decline (negation-aware,
  structural hedged/hard decision -- no length proxy), the
  reachability protocol that found the dead markers, and check-G
  probe sanity. Swap into scoring requires a parity test first.
  Reachability example: examples/reachability_reader_corpus.py
  (measured on a two-reader 758-row sample: 14/21 default markers
  dead; the single strongest canonical rule is the grounding form
  the default list lacks entirely)
- P-0 index paraphrase-flip test (tests/test_paraphrase_flip.py):
  the memory-side denominator for the P-series. Stem-preserving
  paraphrase cannot flip the index; stem-replacing paraphrase must.
  Fixed-input bounds so P-series reader absences subtract index
  misses instead of guessing. First paraphrase attempt leaked the
  stem "tower" through the unrelated tower/moss record -- the
  near-miss the test exists to catch in probe design
- T2 supersession links (v18 port): scenario-declared (old, new)
  pairs, corpus-grounded (ungrounded drop on the record),
  deterministic context line at probe time; measured null on
  shouted mutations (note/nonote identical, f9 NEW-OK both arms)
- T1 BADE revision trials (v18 port): time-aware retrieval
  (turn_of/max_turn -- probes read the corpus as of a turn),
  two-pass prior/posterior with PRIOR-OK/MISSING x
  REVISED/STUCK/LOST/MIXED verdicts; B1-B4 4/4 on base fiction
  (prior "Old Mill" -> revised "Stone Bridge", retention 18/21)
- Headline recall guard: control arms (-nonote) and instruments
  excluded from the retention count by construction
- Scenario channel: supersessions + bade_trials keys, shape-checked
  at load; fiction-v1 (old mill -> stone bridge, plant-5) and
  causeway-v1 (dried well -> watchtower, plant-3) carry their trials
- EVIDENCE: lambda Pareto table (math 0.36 / unk 0.264) + T-series
  section (BADE/supersession verdicts, f3 grab observation)

## [0.1.0] — research preview
- Verbatim turn log of record; sentence corpus + stemmed inverted
  index retrieval with typed absence
- Canonical fact tier with utility-density wall, probationary
  admission, wall-as-rehearsal semantics
- Ghost ledger with eviction provenance + causal needed-by links
- Meta-namespace: schema-gated operational lessons, persisted
- Verdict taxonomy (MISS / CONFABULATE / ADJACENT / ABSTAIN-PLUS /
  HIT) with decline-wins scoring, normalization, stoplists
- Session-isolated SQLite persistence (WAL), sealed blobs with
  hash-chain verification, multi-agent claims with
  disagreement-as-new-file + ACLs
- Read contract with typed absence in the response schema
- Eval extensions: paraphrase retrieval-use probes, conflict
  probes (record-vs-parametric + provenance citation)
- Measured: 18/21 recall home ground, 16–19/21 transfer runs,
  fabrication floor 73–90% (3B) / 21% (12B), discriminability
  d' negative (3B) → positive (12B)
