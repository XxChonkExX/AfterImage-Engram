# Architecture

Afterimage is a memory system for small language models, organized
as a strict separation between a **verbatim store of record**, a
**presentation layer**, and an **answer-time retrieval contract**.
Everything deterministic is text math; everything learned sits
behind a contract (see [TRANSFERABILITY.md](TRANSFERABILITY.md)).

## The layer model

```
+----------------------------------------------------------+
|  READER (any small causal LM, config-selected)           |
|  reads SHORT CONTEXT ONLY: retrieved records or the      |
|  typed-absence line. Never the raw wall, never the log.  |
+----------------------------------------------------------+
                 ^ retrieval        | answer
                 | (indexed,        v
                 |  stemmed,        scoring (verdict taxonomy:
                 |  typed absence)  HIT/MISS/CONFABULATE/ADJACENT/
                 |                  ABSTAIN-PLUS, decline-wins)
+----------------+------------------+-----------------------+
|  WALL (presentation layer, top-K utility-ordered)        |
|  rehearsal: appearance = +1 sighting (Ebbinghaus)        |
+----------------+------------------------------------------+
|  TIER (the fact index: sightings, recency, utility)      |
+----------------+------------------------------------------+
|  GHOST LEDGER (eviction provenance: what/when/why)       |
+----------------+------------------------------------------+
|  META-NAMESPACE (schema-gated self-lessons, persisted)   |
+----------------+------------------------------------------+
|  TURN LOG OF RECORD (verbatim, append-only, permanent)   |
+----------------------------------------------------------+
```

## The layers, bottom-up

### Turn log of record
Every user turn is retained verbatim, permanently. This is the
store of truth: nothing the system does ever compresses, summarizes,
or destroys it. Sentences are split once and form the retrieval
corpus — the ground-truth memory that answer-time retrieval reads.

### Inverted index (retrieval corpus)
Content terms (stopword-guarded, stem-normalized) map to sentence
ids. Probes look up O(1) per term. The stemmer is an iterative,
length-guarded suffix stripper — its only requirement is
*consistency*: both sides of a match stem identically.

### Tier (the fact index)
Extracted facts live in a canonical-keyed store with sighting
counts, last-seen cycles, and display forms. Keys are normalized
(lowercase, prefix-stripped) so counters *add under the
projection* — four spellings of one referent become one key with
summed weight. Extraction is incremental over new turns only, and
it is idempotent: verbatim sentences produce stable facts, which
is what kills fragment decay structurally.

### Wall (presentation layer)
The wall is a knapsack-bounded (top-K items, char budget) ordered
selection from the tier, ranked by utility density:

    u_i = sightings * exp(-delta_cycles / S) / token_cost

with two structural rules:
- **Probationary admission**: young items (low sightings, recently
  extracted) get reserved slots ordered by exploration (newest,
  least-seen first). New facts get *shown*, then compete on merit.
- **One cap pass**: budgets are never double-spent.

Wall appearance is rehearsal (+1 sighting) — presentation
reinforces. Probe hits are use (+2) — use outweighs residence.

### Ghost ledger (eviction provenance)
Items that leave the wall are recorded — what, when, why — and
remain retrievable. Eviction is never destruction; the periphery
is indexed, and absence is always answerable with provenance.

### Meta-namespace (self-lessons)
The system's operational lessons are first-class memory:
schema-validated entries `{class, terms, remedy}`, derived only
from *measured* failures (verdicts and retrieval counts, never
model self-narrative), persisted across runs, applied at probe
time (leakage stoplists, attribute hints, absence annotations).
Schema-invalid entries are dropped on the record. The recursion —
run, measure, extract lessons, apply — is gated by this schema.

### Seal and integrity
Every compaction artifact is hashed (content-minus-hash), and the
chain is verified at end-of-run. Compaction also runs a
*seal check*: a constrained verdict that the summary does not
contradict the extracted facts, retried once, with UNREADABLE as
an honest failure mode.

## The read path (answer-time)

1. The question's content terms are stemmed.
2. The index returns candidate sentences; top-K above a scored
   threshold join the probe context.
3. If nothing clears the threshold, the context is a
   **typed-absence line**: "No relevant records retrieved." The
   reader is told — absence is delivered, not hidden.
4. The answer is scored on its **assertion segment** only (the
   first sentence, before any list-dump): presence of a fact in
   dumped context is not recall.

This makes the read path a *lens experiment* by construction: the
store is frozen, the lens (what is shown) varies, and any behavior
change is attributable to the read, not the memory.

## The write path (compaction)

Reserve-only triggering: compaction fires when remaining context
drops below twice the generation budget. Every compaction is
witnessed four ways: a pre-compaction verification sweep (facts
re-confirmed in full context), the seal verdict, the content hash
chain, and the trigger log. Nothing is lost without a record;
evictions are recoverable by retrieval.

---
**Michael Harding** — Afterimage. Deterministic memory for small models; measured before shipped.
