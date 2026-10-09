"""afterimage_retrieve.py -- answer-time retrieval. Pure functions
over stored records; no model, no I/O. The read is a lens
experiment by construction: the store is frozen, the read (what
is shown) varies, and any behavior change is attributable to the
read, not the memory."""
import re

from afterimage_text import STOPWORDS, stem

RETRIEVAL_K = 3
RETRIEVAL_THETA = 1


def sentences_of(text, min_len=15):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
            if len(s.strip()) >= min_len]


def build_index(sentences):
    """Inverted index: stemmed content term -> sentence ids."""
    idx = {}
    for i, s in enumerate(sentences):
        for w in {stem(x) for x in re.findall(r"[a-z0-9]+", s.lower())
                  if x not in STOPWORDS and len(x) >= 2}:
            idx.setdefault(w, set()).add(i)
    return idx


def retrieve(index, sentences, question, k=RETRIEVAL_K,
             theta=RETRIEVAL_THETA):
    """Stemmed query terms -> posting union -> top-k records above
    theta, else the typed-absence line. PURE and replay-importable
    (the replay-fidelity rule: simulations import this, never
    reimplement)."""
    qwords = {stem(w) for w in re.findall(r"[a-z0-9]+",
                                          question.lower())
              if w not in STOPWORDS and len(w) >= 2}
    hits = {}
    for w in qwords:
        for i in index.get(w, ()):
            hits[i] = hits.get(i, 0) + 1
    if not hits:
        return "No relevant records retrieved.", 0
    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    top = [sentences[i] for i, s in ranked[:k] if s >= theta]
    if not top:
        return "No relevant records retrieved.", 0
    return "\n".join(top), len(hits)


def resurrect_note(ghost, key):
    """Probe-time ghost recovery, PURE and testable. Deterministic
    archive retrieval: if the probe key matches a ghost entry,
    return an archive-recovery line, else ''. Fires when the fact
    left the presentation but the ledger remembers it."""
    kl = key.lower()
    for g in reversed(ghost):
        if kl in g.get("item", "").lower() or g.get("item",
                                                    "").lower() in kl:
            return ("\n(Archive note: '%s' was recorded at cycle %s.)" %
                    (g["item"], g.get("dropped_at", "?")))
    return ""


def link_ghost(ghost, text, probe_id):
    """Ghost-graph edge: record which probe needed which ghosted
    item (causal context for evictions). f-probes pass the expected
    token; miss rows pass the answer segment (captures what the
    model actually used, grabs included)."""
    tl = text.lower()
    for g in ghost:
        it = g.get("item", "").lower()
        if tl and it and (tl in it or it in tl):
            nb = g.setdefault("needed_by", [])
            if probe_id not in nb:
                nb.append(probe_id)
