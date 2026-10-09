"""afterimage_text.py -- pure text utilities. No model, no torch,
no I/O: stdlib re only. These are the deterministic atoms the whole
system is built from; every one is unit-tested for consistency
(both sides of a match must normalize identically)."""

import re

STOPWORDS = {"the", "a", "an", "is", "was", "are", "were", "what",
             "when", "where", "who", "how", "does", "did", "do",
             "of", "at", "in", "on", "to", "for", "and", "or",
             "say", "says", "state", "give", "confirm", "true"}
PRONOUN_GUARD = {"her", "his", "the", "its", "their", "she", "he",
                 "they", "a", "an"}
ORDINALS = {"1st": "first", "2nd": "second", "3rd": "third"}


def stem(w):
    """Porter-class suffix stripper, iterative with min-length-4
    guard: consistency over linguistics. leader==leads,
    closes==closing, rivers==river (both sides stem identically,
    which is all retrieval and scoring need)."""
    for _ in range(2):
        for suf in ("ing", "ed", "er", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        else:
            break
    return w


def canon(x):
    """Canonical projection for tier/store keys: lowercase, strip
    id markers and leading filler verbs, collapse whitespace.
    Counters ADD under this projection (fragments merge)."""
    x = x.lower().strip()
    x = re.sub(r"^\[id\]\s*", "", x)
    x = re.sub(r"^(identify|the|a|an|is|was)\s+", "", x)
    return re.sub(r"\s+", " ", x).strip(" .,;:'\"")


def normalize(s):
    """Ordinal expansion + stemming, for exact-token keys.
    '1st snowfall' -> 'first snowfal' so 'first snow' matches."""
    s = s.lower()
    for k, v in ORDINALS.items():
        s = re.sub(r"\b" + k + r"\b", v, s)
    return " ".join(stem(w) for w in re.findall(r"[a-z0-9]+", s))


def answer_segment(ans):
    """Score the ASSERTION, not the regurgitation. Cut at list-dump
    markers, bullet runs, and 150 chars. Presence in a dumped list
    is disposition-theater; only the asserted sentence counts."""
    seg = re.split(r"\s-{3,}\s|\n\s*[-*\d]+[.)]\s", ans)[0]
    seg = re.split(r"\n", seg)[0]
    return seg[:150]


def sentences_of(text, min_len=15):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
            if len(s.strip()) >= min_len]
