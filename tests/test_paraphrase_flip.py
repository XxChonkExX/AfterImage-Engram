"""P-0: index-level paraphrase flip rate -- the memory-side half of the
P-series. Stdlib only. Run: python tests/test_paraphrase_flip.py

The P-series (docs/EVAL_EXTENSIONS.md) asks whether the READER declines
honestly when the index retrieves nothing for a paraphrase of a planted
fact. That question needs a denominator: how often does the INDEX itself
flip hit->miss under paraphrase, with no reader involved?

Mechanism (measured in the crucible program, 2026-10-17): a query's
content span is the only substrate prompt-conditioned signal lives in;
rewording replaces it. For a stemmed inverted index the prediction is
sharper: a paraphrase that preserves the content stems cannot flip;
a paraphrase that replaces them must flip. This test pins both bounds
on fixed inputs, so the P-series can subtract index misses from reader
behavior instead of guessing.

Deterministic: fixed records, fixed paraphrase pairs, fixed expectations.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import afterimage_retrieve as LR  # noqa: E402

FAILS = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


RECORDS = [
    "The lighthouse keeper's daughter was named Mira Solano.",
    "The stone bridge at the old mill was built in the year 1214.",
    "Blue moss grows only on the north face of the tower.",
    "The nightingale sings at first snow, the keeper wrote.",
]

# paraphrase pairs: (query, paraphrase, flips?)
# -- stem-preserving paraphrase: content stems survive -> must NOT flip
SAME_STEM = (
    "Who was the lighthouse keeper's daughter named?",
    "What was the name of the daughter of the keeper at the lighthouse?",
)
# -- stem-replacing paraphrase: content stems replaced -> must flip
# (every content stem differs from the records: parent/call/youngest/child
#  appear nowhere; the first attempt leaked the stem "tower" via the
#  unrelated tower/moss record -- exactly the near-miss this test exists
#  to catch in probe design)
NEW_STEM = (
    "Who was the lighthouse keeper's daughter named?",
    "What did the parents call their youngest child?",
)


def hits(index, sents, q):
    ids, n = LR.retrieve_ids(index, sents, q)
    return len(ids)


def main():
    sents = list(RECORDS)
    index = LR.build_index(sents)

    # sanity: the base queries retrieve
    check("base query retrieves",
          hits(index, sents, SAME_STEM[0]) > 0)

    # stem-preserving paraphrase: no flip
    a0, a1 = hits(index, sents, SAME_STEM[0]), \
        hits(index, sents, SAME_STEM[1])
    check("stem-preserving paraphrase does not flip (%d -> %d)"
          % (a0, a1), (a0 > 0) == (a1 > 0))

    # stem-replacing paraphrase: flips to typed absence
    b0, b1 = hits(index, sents, NEW_STEM[0]), \
        hits(index, sents, NEW_STEM[1])
    check("stem-replacing paraphrase flips (%d -> %d)" % (b0, b1),
          b0 > 0 and b1 == 0)

    # the flip is the typed-absence line, not a crash or a wrong record
    out, n = LR.retrieve(index, sents, NEW_STEM[1])
    check("flipped retrieval returns the typed-absence line",
          out == "No relevant records retrieved." and n == 0)

    # flip rate is bounded away from 0 and 1 on this fixed pair set:
    # exactly one of the two paraphrase classes flips. That bound is the
    # number the P-series subtracts from reader-side absence behavior.
    flips = sum(1 for pair, expect_flip in
                ((SAME_STEM, False), (NEW_STEM, True))
                for _ in [None]
                if (hits(index, sents, pair[1]) == 0) != \
                   (hits(index, sents, pair[0]) == 0))
    check("flip count matches expectation (1 of 2 classes)", flips == 1)

    print()
    if FAILS:
        print("%d FAIL: %s" % (len(FAILS), "; ".join(FAILS)))
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()