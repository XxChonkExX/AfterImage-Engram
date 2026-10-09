# Afterimage

> **Memory that outlives its context.** A deterministic memory engram
> for small language models.

Afterimage is a CPU-native, model-agnostic memory system for small
local LLMs. It keeps a verbatim log of record, retrieves from it with
a stemmed inverted index, presents a utility-ordered working set,
records every eviction with provenance, scores honesty with a typed
verdict taxonomy, and remembers its own operational lessons — all
deterministic, all pure text math, no vector database, no embeddings,
no GPU.

**Status: research preview.** The architecture and eval suite are
complete and measured; the packaging refactor is in progress. See
[docs/EVIDENCE.md](docs/EVIDENCE.md) for the measured results and
[docs/ROADMAP.md](docs/ROADMAP.md) for what lands next.

---

## The problem it addresses

Small local models confabulate. We measured it: **73–100% of
questions about absent content receive confident fabricated answers**,
across four read-path configurations, and the discriminability metric
(signal detection theory d′) is **negative** — a small model cannot
tell "I know this" from "this doesn't exist."

Afterimage does not fix that. **Nothing memory-side can** — we
measured it four ways, and the floor is reader disposition, which is
training-side. What Afterimage does:

1. **Guarantee delivery** — the right records are retrieved and
   presented, with provenance, every time
2. **Detect absence** — typed absence is a first-class answer with a
   scored taxonomy (MISS / CONFABULATE / ADJACENT / ABSTAIN-PLUS)
3. **Measure the floor honestly** — the eval suite ships with the
   system, and the fabrication floor is a first-class acceptance
   number, not a benchmark afterthought

The memory system and the training objective are complementary
halves: the engram delivers the truth; a decoder trained with the
miss objective (the absence-decline behavior in its training data)
learns to respect it. Neither alone is sufficient. We measured that.

---

## The transfer matrix (measured)

| Ground | Run | Recall (planted facts) | Notes |
|---|---|---|---|
| Home scenario | tuned | **18/21 (86%)** | high-water; lessons applied |
| New scenario, first contact | transfer run | 16/21 (76%) | never-seen domain, 2 owned bugs |
| New scenario, tuned + lessons | recursion run | **19/21 (90%)** | new ground, *above* home |
| (fabrication floor, all runs) | — | **73–100% on absent content** | reader disposition; the training target |

Same store mechanics, different scenario surface, lessons carried
across the boundary. The full numbers, methods, and falsifier
scorecards: [docs/EVIDENCE.md](docs/EVIDENCE.md).

---

## Design principles

1. **Store of record.** The verbatim log is append-only and never
   compressed away. The wall is presentation, not truth.
2. **Typed absence.** "No record" is a structured answer with
   provenance — not silence for the reader to fill with invention.
3. **Ghost ledger.** Nothing is evicted without a record of what and
   why. Evicted facts are recoverable by retrieval.
4. **Decline-wins.** Honest failure beats fabricated success — in
   scoring, in targets, and in training data.
5. **Falsifier-first.** Every mechanism ships with the eval that can
   break it. Predictions are registered before runs.
6. **Deterministic is portable; learned is fitted.** The math is the
   universal wire interface (see the ledger); learned components sit
   behind contracts and carry stamps.

---

## What it is not

- **Not a vector database.** Retrieval is a stemmed inverted index
  with typed absence — exact, auditable, and calibrated, not
  similarity-vibes.
- **Not RAG context-stuffing.** Retrieval is a contract with
  provenance and absence semantics, not context maximization.
- **Not a fine-tune.** The reader model is untouched; the memory
  lives outside the weights, which is why it transfers.
- **Not a cure for confabulation.** Measured, guaranteed delivery
  and honest scoring — the cure is a training objective, and
  Afterimage ships its eval.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — the layer model, store
  semantics, and the read/write paths
- [Math Ledger](docs/MATH_LEDGER.md) — the portable core: eight
  formal methods, each mapped to a measured problem
- [Transferability](docs/TRANSFERABILITY.md) — what transfers across
  models and domains, what re-fits, and the contract that keeps
  learned components contained
- [Evidence](docs/EVIDENCE.md) — the measured results: transfer
  matrix, SDT decomposition, fabrication floors, falsifier
  scorecards
- [Roadmap](docs/ROADMAP.md) — registered triggers, staged work, and
  what would make us wrong

---

## Status and roadmap

Research preview. One reader fully evaluated (3B-class, CPU); a 12B
reader evaluation in flight; one scenario domain fully specified plus
a variant (the scenario-as-data path is proven). The packaging
refactor — scenario files, model config, and the library interface —
is the current workstream.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the staged plan and the
registered triggers that gate each stage.

## Related work (September 2026 cluster)

The small-model memory niche heated up fast. Four current papers
work adjacent ground; each is missing something Afterimage ships:

- **Learning from Failures (arXiv 2609.28003)** — heterogeneous
  graph memory preserving causal context of failed actions. The
  closest cousin to our ghost ledger. What they lack: falsifiers,
  a scoring taxonomy, and any abstention measurement.
- **From Retrieval to Weights (arXiv 2609.10155)** — per-corpus
  DoRA adapters writing retrieved text into small-model weights.
  Validates the adapter direction; has no abstention gate, which
  is exactly what our eval stack supplies.
- **RAIM (arXiv 2609.39229)** — aggregating cheap models for
  hallucination detection. Our cross-reader verdict agreement is
  the same instinct with measured per-reader baselines.
- **PASC (arXiv 2605.18812)** — joint coverage guarantees across
  multi-stage pipelines. The formal version of our coupled-
  metrics gate.

What none of them ship: a fabrication floor measured on absent
content, a per-fact retention curve, a miss taxonomy with
falsifiers, or a discrimination metric (d′) separating reader
knowledge from reader disposition. The niche has builders; it
has no measurers. That is this repo's position.

Note on scope: frontier labs certainly hold unpublished work in
this space. Our claims are against the published record only —
and against our own falsifiers first.

## Author

**Michael Harding** — design, architecture, and the measurement
discipline. Built with an AI research partner (the harness runs,
the instruments judge); every claim in these documents carries its
own falsifier.

*"Theories are meant to die under testing or stand under rigor and
repeatability. That is the truth."*
