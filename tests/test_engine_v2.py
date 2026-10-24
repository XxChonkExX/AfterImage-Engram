"""Smoke test for afterimage_engine_v2: channels + fusion + contract."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from collections import Counter

from afterimage_engine_v2 import (  # noqa: E402
    Retriever, chunk_record, expand, terms, rrf, _ranks)


def test_chunking_keeps_blocks():
    txt = "GOBLIN\n\nAC 15  HP 7\nSpeed 30 ft.\n\nSmall humanoid."
    chunks = chunk_record(txt)
    assert any("AC 15" in c and "Speed" in c for c in chunks)


def test_synonyms_expand():
    assert "armor" in expand(terms("ac"))


def test_retrieval_returns_correct_record():
    recs = [
        "The goblin has armor class 15 and 7 hit points.",
        "The dragon breathes fire in a 30-foot cone.",
        "Grappling: the target is grappled with escape DC 14.",
    ]
    r = Retriever(recs)
    got, n = r.search("goblin armor class", k=1)
    assert "goblin" in got.lower()


def test_typed_absence_contract():
    r = Retriever(["The goblin has armor class 15."])
    got, n = r.search("qwertyuiop zxcvbnm", k=1)
    assert got == "No relevant records retrieved." and n == 0


def test_rrf_prefers_consensus():
    a = _ranks(Counter({0: 5, 1: 3, 2: 1}))
    b = _ranks(Counter({1: 5, 0: 1}))
    f = rrf([a, b])
    assert f.most_common(1)[0][0] in (0, 1)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
    print("ALL PASS")

