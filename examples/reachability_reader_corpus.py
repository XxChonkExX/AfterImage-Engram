"""reachability_reader_corpus.py -- run the decline-marker reachability
protocol against a reader-transcript archive. Side effects live here
(examples/), per repo rules; the logic it calls is pure.

Why: hand-written decline vocabularies fail silently. Measured on
6,113 real reader outputs (2026-10-17): 8 of 21 DEFAULT_DECLINE_MARKERS
never fired, and the vocabulary missed 67% of the declines a validated
classifier found -- mostly grounding-based declines ("I cannot see...",
"I can't tell you what you dreamed"), which are the dominant decline
form in small readers. A dead decline marker is not a cosmetic gap:
miss_verdict checks decline BEFORE content keys, so a missed decline
falls through to bare-assertion and can score CONFABULATE.

Usage:
  python examples/reachability_reader_corpus.py <transcripts.jsonl> [more.jsonl ...]

Each jsonl row needs an "output" (or "seg") field. Nothing is written;
counts print to stdout. Point it at any reader corpus -- the numbers
are per-corpus by design.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import afterimage_decline as AD  # noqa: E402
import afterimage_score as LS  # noqa: E402

from afterimage_score import DEFAULT_DECLINE_MARKERS  # noqa: E402


def load(paths):
    texts = []
    for p in paths:
        for f in (glob.glob(p) or [p]):
            if not os.path.exists(f):
                print("skip (not found): %s" % f)
                continue
            for line in open(f, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                t = (r.get("output") or r.get("seg") or "").strip()
                if t:
                    texts.append(t)
    return texts


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    texts = load(sys.argv[1:])
    if not texts:
        print("no rows loaded; nothing to measure")
        sys.exit(1)
    print("reader outputs: %d" % len(texts))

    print("\n== DEFAULT_DECLINE_MARKERS (afterimage_score) ==")
    theirs = AD.reachability(DEFAULT_DECLINE_MARKERS, texts)
    dead = [p for p, n in theirs.items() if n == 0]
    for pat, n in sorted(theirs.items(), key=lambda kv: -kv[1]):
        print("  %s %5d  %s" % ("DEAD " if n == 0 else "live", n, pat))
    print("  DEAD: %d/%d" % (len(dead), len(DEFAULT_DECLINE_MARKERS)))

    print("\n== vendored canonical rules (afterimage_decline) ==")
    ours = AD.reachability(
        [p.strip() for p in AD._DECLINE], texts)
    dead_ours = [p for p, n in ours.items() if n == 0]
    for pat, n in sorted(ours.items(), key=lambda kv: -kv[1]):
        print("  %s %5d  %s" % ("DEAD " if n == 0 else "live", n, pat))
    print("  DEAD: %d/%d" % (len(dead_ours), len(ours)))

    declines = sum(1 for t in texts if AD.decline_or_none(t))
    caught = sum(1 for t in texts
                 if AD.decline_or_none(t)
                 and any(__import__("re").search(p, t.lower())
                         for p in DEFAULT_DECLINE_MARKERS))
    print("\ncanonical declines: %d" % declines)
    print("  caught by DEFAULT vocabulary: %d (%.0f%%)"
          % (caught, 100 * caught / max(1, declines)))
    print("  missed: %d -- these fall through to default-MISS and can"
          % (declines - caught))
    print("  mislabel via bare-assertion when the answer echoes topic content")
    print("\nTrade note: if the missed share is high on YOUR reader,"
          " consider adding the missed phrasings to your domain config's"
          " decline list (config-driven, per docs/EVAL_EXTENSIONS.md),"
          " and record the reachability run that justified it.")


if __name__ == "__main__":
    main()