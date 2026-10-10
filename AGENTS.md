# AGENTS.md — Afterimage

Instructions for AI coding agents working in this repository.
Humans: most of this is good practice for you too.

## What this repo is

A deterministic memory engram for small language models. Pure
stdlib Python (3.10+), zero runtime dependencies, no model, no
GPU, no network. The library (`src/afterimage_*.py`) is the
product; `tests/`, `examples/`, and `docs/` ship with it.
Design rationale and measured results live in `README.md` and
`docs/EVIDENCE.md` — read those before changing anything.

## Non-negotiables

1. **Zero dependencies.** No new imports beyond the stdlib. If
   a change needs a package, the change is wrong (propose it in
   an issue instead).
2. **Pure functions in `src/`.** No I/O, no prints, no globals
   mutated, no network. Side effects live in `examples/` and
   `tests/` only.
3. **Don't reimplement — import.** Simulations and new tools
   import `afterimage_*` modules (the replay-fidelity rule). A
   private copy of a function is a bug waiting to diverge.
4. **Never edit frozen artifacts.** `examples/*.json` are
   scenario instruments (future hash-pinned); banked run
   records are never rewritten. New data = new files.
5. **Byte discipline.** `.gitattributes` pins LF. If a fresh
   clone shows modified files, run `git add --renormalize .`
   and report it — a CRLF flip on a scenario JSON will fail a
   digest gate exactly like tampering.

## Before you commit

- Run the suite (all four, they are fast):
  ```bash
  python tests/test_store.py
  python tests/test_rungs.py
  python tests/test_library.py
  python tests/replay_v171b.py
  ```
- New behavior → new test in `tests/test_library.py` (stdlib
  only; torch-dependent code is NOT allowed in this repo).
- New module → add one line to the module map in `INSTALL.md`.
- Behavior change → one line in `CHANGELOG.md` (newest first),
  including negative results — "tried X, it failed because Y"
  is a first-class changelog entry here.

## Conventions

- Docstrings carry the design rationale, not just signatures.
  If you had to read three files to understand why something is
  shaped oddly, that shape probably encodes a measured lesson —
  keep the comment, extend it, never strip it.
- Scoring order is doctrine (see `afterimage_score.py`
  docstring): anchors → correction-first → decline-wins →
  stoplists → keys → bare-assertion → default MISS. Do not
  reorder without a test proving the old order wrong.
- Honest failure is a first-class outcome. The taxonomy
  (MISS / CONFABULATE / ADJACENT / ABSTAIN-PLUS / HIT) exists
  so failure and fabrication are distinguishable — never
  "improve" a result by making failures look like successes.
- Evidence over vibes: claims in docs cite artifacts. If you
  add a claim, add the artifact path or the test that proves it.

## Research vs product

The versioned research harnesses (`engram_harness_v*.py`) are
NOT in this repo — they live in the operator's project tree.
This repo ports their *validated* mechanics, with byte-for-byte
parity tests enforced in `tests/test_library.py`. If library
and harness disagree on fixed inputs, **the library is wrong**;
fix the port, never redefine the test.

## House style

- No emojis, no marketing adjectives, no "revolutionary".
- Negative results are recorded, not hidden.
- Commit messages: plain subject line, what and why, no fluff.
- Every prediction that precedes a measurement is registered
  in writing first (see docs/EVIDENCE.md for the pattern).
  Falsifier-first is the house epistemics.

— Michael Harding / Afterimage
