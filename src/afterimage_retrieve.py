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


def retrieve_ids(index, sentences, question, k=RETRIEVAL_K,
                 theta=RETRIEVAL_THETA, turn_of=None, max_turn=None):
    """Retrieval core: ranked sentence ids above theta (top-k) + the
    full hit count. PURE. turn_of/max_turn implement time-aware
    retrieval (T1 BADE): with max_turn set, only sentences from
    turns <= max_turn are eligible, so a probe can read the corpus
    AS OF a turn (the pre-disconfirmation prior is real, not
    notional). turn_of is a list parallel to sentences (the library
    holds no globals); turn_of=None or max_turn=None is the
    unfiltered read."""
    qwords = {stem(w) for w in re.findall(r"[a-z0-9]+",
                                          question.lower())
              if w not in STOPWORDS and len(w) >= 2}
    hits = {}
    for w in qwords:
        for i in index.get(w, ()):
            if max_turn is not None and turn_of is not None \
                    and i < len(turn_of) and turn_of[i] > max_turn:
                continue
            hits[i] = hits.get(i, 0) + 1
    if not hits:
        return [], 0
    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    ids = [i for i, s in ranked[:k] if s >= theta]
    return ids, len(hits)


def retrieve(index, sentences, question, k=RETRIEVAL_K,
             theta=RETRIEVAL_THETA, turn_of=None, max_turn=None):
    """Stemmed query terms -> posting union -> top-k records above
    theta, else the typed-absence line. PURE and replay-importable
    (the replay-fidelity rule: simulations import this, never
    reimplement)."""
    ids, n = retrieve_ids(index, sentences, question, k=k,
                          theta=theta, turn_of=turn_of,
                          max_turn=max_turn)
    if not ids:
        return "No relevant records retrieved.", 0
    return "\n".join(sentences[i] for i in ids), n


def build_supersessions(corpus_text, pairs):
    """T2 grounding, PURE: keep (old, new) pairs whose BOTH endpoints
    appear in the corpus (case-insensitive); the rest drop ON THE
    RECORD. A mutation is a first-class deterministic entry, not an
    emergent retrieval property."""
    hay = corpus_text.lower()
    active, dropped = [], []
    for p in pairs:
        if p.get("old", "").lower() in hay and \
                p.get("new", "").lower() in hay:
            active.append({"old": p["old"], "new": p["new"]})
        else:
            dropped.append(dict(p))
    return active, dropped


def supersession_note(matched_sentences, links):
    """T2 read-path, PURE: deterministic context line iff a retrieved
    record carries a superseded term. Never model prose."""
    for s in matched_sentences:
        low = s.lower()
        for l in links:
            if l["old"].lower() in low:
                return ("[supersession: '%s' was superseded by '%s' "
                        "-- answer with the current value.]"
                        % (l["old"], l["new"]))
    return ""


def bade_verdict(seg1, seg2, old, new):
    """T1 BADE verdict, PURE: prior establishment x posterior
    revision. PRIOR-OK/MISSING x REVISED/STUCK/LOST/MIXED."""
    s1, s2 = seg1.lower(), seg2.lower()
    prior = "PRIOR-OK" if old.lower() in s1 else "PRIOR-MISSING"
    has_new = new.lower() in s2
    has_old = old.lower() in s2
    if has_new and not has_old:
        post = "REVISED"
    elif has_old and not has_new:
        post = "STUCK"
    elif has_new and has_old:
        post = "MIXED"
    else:
        post = "LOST"
    return prior + "-" + post


def resolve_turn(tag, turn_tags):
    """T1 tag resolution, PURE: symbolic turn tag -> corpus index."""
    return turn_tags.get(tag)


def retention_count(results):
    """Headline recall count, PURE: recorded HIT/NEW-OK only. Control
    arms (-nonote) and instruments (miss/, bade/) are excluded -- an
    ablation must never inflate the headline it controls."""
    return sum(1 for k, v in results.items()
               if not k.endswith("-nonote") and
               (v.get("recalled") or v.get("recalled_new")))


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
