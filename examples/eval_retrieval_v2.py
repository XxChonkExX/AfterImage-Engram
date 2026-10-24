"""Known-item recall harness: baseline (hit-count, current AfterImage)
vs BM25 vs RRF fusion, on the rpg_store engram (read-only).

For each sampled record we build a 3-content-term query from a SUBSET of
its own terms (discrimination test, not exact-match), then check whether
any unit of that record lands in top-k. Honest, deterministic, label-free.
"""
import os
import random
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from afterimage_engine_v2 import Index, Retriever, terms, _ranks, rrf  # noqa: E402

RPG_DB = r"D:\AI_Bundle\engram_personal\rpg_store\engram.db"
ALLOW = ("srd51", "pf1e")


def load_records(limit_sessions=None):
    con = sqlite3.connect(f"file:{RPG_DB}?mode=ro", uri=True)
    recs = []
    for sid, text in con.execute("SELECT session_id, text FROM records"):
        if not sid.startswith(ALLOW):
            continue
        t = text.strip()
        if 80 <= len(t) <= 4000:
            recs.append((sid, t))
    con.close()
    return recs


def baseline_hits(idx, qt):
    """Current AfterImage scoring: raw query-term hit count."""
    hits = Counter()
    for w in set(qt):
        for i in idx.postings.get(w, ()):
            hits[i] += 1
    return hits


def main():
    random.seed(7)
    recs = load_records()
    print(f"[corpus] {len(recs)} records", flush=True)
    texts = [t for _, t in recs]
    ret = Retriever(texts)
    idx = ret.idx
    print(f"[units] {len(ret.units)} chunks", flush=True)

    # map unit -> source record
    sample = random.sample(range(len(texts)), 500)
    N = len(texts)
    r_at = {"baseline": 0, "bm25": 0, "rrf": 0}
    K = 5
    for si in sample:
        qt = terms(texts[si])
        if len(qt) < 4:
            continue
        q3 = random.sample(qt, 3)
        qstr = " ".join(q3)
        src = ret.src  # unit -> source record index

        # baseline
        bh = baseline_hits(idx, q3)
        btop = [i for i, _ in bh.most_common(K)]
        if any(src[i] == si for i in btop):
            r_at["baseline"] += 1

        # bm25
        bm = idx.bm25(q3)
        if any(src[i] == si for i, _ in bm.most_common(K)):
            r_at["bm25"] += 1

        # rrf (full pipeline over unit ids)
        fused = rrf([_ranks(idx.bm25(q3)),
                     _ranks(idx.phrase(q3)),
                     _ranks(idx.charngram(qstr))])
        rtop = [i for i, _ in fused.most_common(K)]
        if any(src[i] == si for i in rtop):
            r_at["rrf"] += 1

    n = len(sample)
    for k, v in r_at.items():
        print(f"  {k:9s} R@{K} = {v}/{n} = {v/n:.3f}")


if __name__ == "__main__":
    main()

