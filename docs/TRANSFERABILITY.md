# Transferability — the contract

The engram's value claim is portability: the same core, wired to
different readers and different domains, with bounded, known re-fit
costs. This document is the contract that makes that true rather
than aspirational.

## The thesis

**Deterministic is portable; learned is fitted.**

Every deterministic component — the log, the index, the tier, the
wall, the ghost ledger, the scoring taxonomy, the math — is a pure
function of text and counters. It transfers across readers,
domains, and hardware unchanged. Every learned or tuned component
is domain-fitted by design, sits behind a text-in/score-out
contract, and carries stamps identifying what it was fitted to.

## What transfers unchanged

- The turn log of record (verbatim, append-only)
- The inverted index and stemmer (pure text functions)
- The tier structure and canonical projection
- The wall assembly (density ordering, probation admission)
- The ghost ledger and its semantics
- The verdict taxonomy and scoring order
- The math ledger (all of it)
- The falsifier suite and eval discipline

## What re-fits per reader (the reader-coupled surface)

Extraction prompts, probe phrasing, and answer-segment markers are
tuned to the *current reader's observed failure modes* (for
example: one reader's repetition loops, another's list-dump habits).
These are the engram's equivalent of a hardware driver: the
mechanism is general, the tuning is per-device. Re-fitting is cheap
by design — the harness generates its own labeled run data on any
reader it is pointed at, so re-validation is an operation, not a
rebuild.

## What re-fits per domain

- The planted-value and planted-name inventories (ground-truth
  vocabularies)
- The decline-marker vocabulary (language-dependent)
- The miss-probe set (scenario-authored, class-preserving: the
  *classes* — absent entity, identity gap, transposed value,
  negation inversion — are universal; the instances are per-domain)

## The learned-component rule

If a learned component ever becomes necessary (the registered
trigger: retrieval fails on semantically-bridging misses after the
lexical baseline is exhausted), it must:

1. Sit behind a `text-pair -> score` contract
2. Carry version + domain + reader stamps
3. Be re-fit — not rebuilt — per reader/domain from
   harness-generated data

The trigger was registered *before* the component exists, and the
first cross-domain evaluation determines whether it fires at all.

## The scenario-as-data interface

Scenarios are JSON, not code:

    facts            ground-truth statements (the probes' targets)
    probe_keys       exact-token expectations per fact
    fid_attr         attribute disambiguation hints
    plant_turns      the turns that carry the facts
    mutate_turn      a mid-run value supersession (invalidation probe)
    distract_turns   plausible-but-irrelevant pressure turns
    miss_rows        absent-content probes: pid, question, key
                     patterns, expectation
    planted_values   the value stoplist (leakage detection)
    planted_names    the name stoplist

A scenario swap is a data edit. The mechanics are code. That
separation *is* the portability claim, enforced by the loader.

## The measured transfer result

First-contact transfer to an unseen scenario (different names,
values, and phrasing; identical 14-fact structure):

- Recall 16/21 (76%) on first contact — no scenario-specific tuning
- 19/21 (90%) after scenario-tuned scoring — the re-fit cost was
  key normalization and two attribute hints
- The failure classes on new ground were *the same classes* as
  home ground (attribute binding, morphological gaps) — the
  taxonomy transfers even where the specific keys needed tuning

Full data: [EVIDENCE.md](EVIDENCE.md).

---
**Michael Harding** — Afterimage. Deterministic memory for small models; measured before shipped.
