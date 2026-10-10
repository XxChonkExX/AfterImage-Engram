# Install & run — Afterimage

Zero runtime dependencies. Pure-stdlib Python 3.10+. No model,
no GPU, no vector database, no network calls. Anything below
that fails is an environment problem, never a missing service.

## Requirements

- Python **3.10+** (`python --version`)
- `pip`, `git`
- OS: Linux / macOS / Windows (CI runs all three × 3.10/3.12/3.14)

## Install

```bash
git clone https://github.com/XxChonkExX/AfterImage-Engram.git
cd AfterImage-Engram
pip install -e .
```

That is the whole install. `pip install -e .` registers the
`afterimage_*` modules from `src/`; there is nothing else to
fetch, build, or configure.

## Verify: the test suite

```bash
python tests/test_store.py     # session persistence, seals, blobs
python tests/test_rungs.py     # production rungs 2-4
python tests/test_library.py   # module parity + scorer batteries
python tests/replay_v171b.py   # frozen-run replay (see note)
```

All four must print PASS/DONE with no failures. Notes:

- `test_library.py` is torch-free: the harness-parity section
  detects the research harnesses and **skips cleanly** when they
  are absent (CI included). Everything else runs on stdlib.
- `replay_v171b.py` replays a frozen run; off-box without the
  frozen artifacts it skips cleanly instead of failing.
- Torch is **never** required. If any test imports torch
  unguarded, that is a bug — file it.

## Run the demo (no model calls)

```bash
python examples/run_scenario.py                        # fiction-v1
python examples/run_scenario.py examples/causeway-v1.json
```

A full deterministic pass over a scenario JSON: extract, tier,
wall, miss probes through retrieval + scorer, supersession
grounding, BADE trials through the stub reader, falsifier
scorecard. Same JSON in, same verdicts out, on any machine.
The stub reader echoes context (deterministic); a real reader
substitutes at the documented call site.

## Library map (`src/`, one line each)

| Module | Job |
|---|---|
| `afterimage_text` | deterministic atoms: stem, normalize, canon, stopwords |
| `afterimage_extract` | regex fact extraction (strings, never referents) |
| `afterimage_tiers` | canonical tiers, density wall, probation, ghost ledger |
| `afterimage_retrieve` | stemmed inverted index, time-aware reads, supersession notes, BADE verdicts |
| `afterimage_score` | honesty taxonomy (MISS/CONFABULATE/ADJACENT/ABSTAIN-PLUS/HIT), decline-wins, config-driven domains |
| `afterimage_meta` | schema-gated lesson namespace (persisted operational lessons) |
| `afterimage_scenario` | scenario-as-data loader + validator (fails loud, never silent) |
| `afterimage_store` | SQLite/WAL session persistence, sealed blobs, hash chains |
| `afterimage_api` | product boundary: reads return records-with-provenance or certified absence |

Rule for simulations: **import these, never reimplement**
(replay-fidelity). A port that drifts is a rewrite.

## Scenario files (`examples/`)

`fiction-v1.json` (home ground) and `causeway-v1.json`
(transfer ground). Keys: `facts`, `probe_keys`, `plant_turns`,
`mutate_turn`, `distract_turns`, `miss_rows` (pid/question/keys),
`planted_values/names`, `fid_attr`, `f9_new/f9_old`,
`supersessions` (old/new pairs), `bade_trials`,
`unkeyed_facts` (invalidation-track facts), `cycle_probes`.
`load_scenario()` validates shape and raises listing every
problem — a bad spec fails at load, never at probe time.

## Research lineage (not in this repo)

The versioned research harnesses (`engram_harness_v*.py`) live
outside this package; the library ports their validated
mechanics module by module, with byte-for-byte parity tests.
`tests/test_library.py` enforces the parity. If library and
harness disagree on fixed inputs, the library is wrong.

## Line endings (Windows checkout note)

Scenario JSONs are future hash-pinned instruments, so bytes
matter: `.gitattributes` pins LF for code/data/docs. If a fresh
clone shows modified files immediately, line endings drifted —
run `git add --renormalize .` and report it, do not commit the
noise. (This exact failure — CRLF flipping a pinned digest —
was caught live by a digest gate; the attribute exists so it
cannot recur here.)

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: afterimage_*` | `pip install -e .` not run (or wrong venv) |
| Parity section "skipped" | normal off-box (no research harnesses present) |
| Replay skips | normal off-box (no frozen artifacts present) |
| Python < 3.10 | `X \| Y` type syntax needs 3.10+; upgrade |
| Fresh clone shows dirty tree | line endings (see above), report it |

## What to read next

- [README](README.md) (the problem, the transfer matrix, principles)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (layer model, read/write paths)
- [docs/EVIDENCE.md](docs/EVIDENCE.md) (measured results — predictions before runs)
- [docs/ROADMAP.md](docs/ROADMAP.md) (staged work, registered triggers)
- [CHANGELOG](CHANGELOG.md) (newest first, falsifiers included)
