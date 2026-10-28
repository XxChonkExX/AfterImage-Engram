"""Afterimage v0.2 engine: pure, deterministic retrieval upgrades.

Channels (all pure text math, no embeddings, no GPU):
  - BM25           (IDF x saturating TF x length norm)  [replaces hit-count]
  - phrase/proximity (contiguous bigram/trigram match)
  - char-ngram     (4-gram overlap; OCR/typo robust)
Fusion: Reciprocal Rank Fusion (RRF, k=60). Query expansion: RPG synonyms.
Chunking: structure-aware (markdown blocks, stat blocks, tables kept whole).
"""
import math
import re
from collections import Counter

STOPWORDS = set("""a an the and or but if then else of to in on at for with
from by as is are was were be been being do does did this that these those
it its i you he she they we me my your his her their our not no yes can
will would should could may might must shall have has had""".split())


def stem(w):
    for _ in range(2):
        for suf in ("ing", "ed", "er", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[:-len(suf)]
                break
        else:
            break
    return w


def terms(text):
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in STOPWORDS and len(w) >= 2]


# ---------- D. structure-aware chunking ----------
def chunk_record(text, max_chars=1200):
    """Split a stored record into atomic chunks, keeping markdown tables
    and stat-block line groups intact (blank-line blocks; oversized
    blocks split on sentence boundaries only)."""
    text = text.strip()
    blocks = re.split(r"\n\s*\n", text)
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if len(b) <= max_chars:
            out.append(b)
            continue
        # split long block on sentence boundaries
        cur = ""
        for s in re.split(r"(?<=[.!?])\s+", b):
            if len(cur) + len(s) + 1 > max_chars and cur:
                out.append(cur.strip())
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            out.append(cur.strip())
    return out or [text]


# ---------- C. RPG synonym expansion ----------
SYN = {
    "ac": ["armor", "class"], "armor": ["ac"], "hp": ["hit", "points"],
    "hit": ["hp"], "thac0": ["attack", "roll"], "sdc": ["structural",
    "damage"], "mdc": ["mega", "damage"], "save": ["saving", "throw"],
    "saves": ["saving", "throw"], "str": ["strength"], "dex": ["dexterity"],
    "con": ["constitution"], "int": ["intelligence"], "wis": ["wisdom"],
    "cha": ["charisma"], "pst": ["psionic"], "ppe": ["potential"],
    "xp": ["experience", "points"], "cr": ["challenge", "rating"],
    "npc": ["character"], "dmg": ["damage"], "hd": ["hit", "dice"],
    "sp": ["spell", "points"], "isp": ["inner", "strength"],
}


def expand(qterms):
    out = list(qterms)
    for t in qterms:
        out += [stem(x) for x in SYN.get(t, ())]
    return out


# ---------- A/B. channels ----------
class Index:
    def __init__(self, records):
        self.records = records
        self.doc_terms = [terms(r) for r in records]
        self.tf = [Counter(t) for t in self.doc_terms]
        self.length = [len(t) for t in self.doc_terms]
        self.avg = sum(self.length) / max(1, len(self.length))
        self.postings = {}
        for i, t in enumerate(self.doc_terms):
            for w in set(t):
                self.postings.setdefault(w, set()).add(i)
        self.N = len(records)
        self.df = {w: len(s) for w, s in self.postings.items()}
        # phrase index (contiguous content bigrams)
        self.bigrams = {}
        for i, r in enumerate(records):
            toks = [stem(w) for w in re.findall(r"[a-z0-9]+", r.lower())
                    if w not in STOPWORDS and len(w) >= 2]
            for a, b in zip(toks, toks[1:]):
                self.bigrams.setdefault((a, b), set()).add(i)
        # char 4-grams
        self.ngrams = []
        for r in records:
            core = re.sub(r"[^a-z0-9]", "", r.lower())
            self.ngrams.append({core[i:i + 4]
                                for i in range(max(0, len(core) - 3))})

    def bm25(self, qterms, k1=1.2, b=0.75):
        q = Counter(expand(qterms))
        scores = Counter()
        for w in q:
            df = self.df.get(w, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for i in self.postings[w]:
                f = self.tf[i][w]
                denom = f + k1 * (1 - b + b * self.length[i] / self.avg)
                scores[i] += q[w] * idf * (f * (k1 + 1)) / denom
        return scores

    def phrase(self, qterms):
        scores = Counter()
        for a, b in zip(qterms, qterms[1:]):
            for i in self.bigrams.get((a, b), ()):
                scores[i] += 3.0
        return scores

    def charngram(self, query):
        core = re.sub(r"[^a-z0-9]", "", query.lower())
        qg = {core[i:i + 4] for i in range(max(0, len(core) - 3))}
        if not qg:
            return Counter()
        scores = Counter()
        for i, ng in enumerate(self.ngrams):
            ov = len(qg & ng)
            if ov:
                scores[i] = ov / len(qg)
        return scores


def _ranks(scores):
    return [i for i, _ in scores.most_common()]


def rrf(rank_lists, weights=(1.0, 0.5, 0.3), k=60):
    fuse = Counter()
    for w, rl in zip(weights, rank_lists):
        for rank, i in enumerate(rl, 1):
            fuse[i] += w / (k + rank)
    return fuse


class Retriever:
    def __init__(self, records):
        # D: chunk records into atomic units (keep a back-pointer)
        self.units, self.src = [], []
        for ri, r in enumerate(records):
            for c in chunk_record(r):
                self.units.append(c)
                self.src.append(ri)
        self.idx = Index(self.units)

    def search(self, query, k=5, theta=1, min_score=None):
        """Returns the typed-absence line when nothing clears theta
        (the Afterimage read contract), else the top-k units.

        min_score: optional floor on the top unit's BM25 score. RRF
        ranks are scale-free, so the absolute-relevance gate runs on
        the BM25 channel; queries whose best unit scores under the
        floor get the typed-absence line instead of polluting the
        prompt with unrelated material.
        """
        qt = terms(query)
        if not qt:
            return "No relevant records retrieved.", 0
        bm = self.idx.bm25(qt)
        ph = self.idx.phrase(qt)
        ng = self.idx.charngram(query)
        fused = rrf([_ranks(bm), _ranks(ph), _ranks(ng)])
        if not fused:
            return "No relevant records retrieved.", 0
        if min_score is not None:
            best = max(bm.get(i, 0.0) for i, _ in fused.most_common(k))
            if best < min_score:
                return "No relevant records retrieved.", 0
        top = [i for i, _ in fused.most_common(k)]
        return "\n".join(self.units[i] for i in top), len(fused)

