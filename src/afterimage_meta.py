"""afterimage_meta.py -- the schema-gated self-lesson namespace.
Operational lessons are first-class memory: schema-validated
entries {class, terms, remedy}, derived only from MEASURED
failures, persisted across runs, applied at probe time. Prose
self-narrative is rejected at the gate. The recursion --
run, measure, extract, apply -- is gated by this schema."""
import json
import os

META_SCHEMA = {"class", "terms", "remedy"}
LESSON_CAP = 50


def load_meta(path):
    """Load persisted lessons; validate; drop invalid entries on
    the record. A corrupt lesson is removed, never trusted."""
    try:
        meta = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    ok, dropped = [], 0
    for entry in meta.get("lessons", []):
        if META_SCHEMA.issubset(entry) and isinstance(
                entry.get("terms"), list) and entry["terms"]:
            ok.append(entry)
        else:
            dropped += 1
    return ok[:LESSON_CAP], dropped


def save_meta(lessons, path):
    json.dump({"lessons": lessons[:LESSON_CAP]},
              open(path, "w", encoding="utf-8"), indent=1)


def merge_lessons(existing, candidates):
    """Append candidates, deduped on (class, sorted-terms). Returns
    (merged, n_new)."""
    seen = {(l["class"], tuple(sorted(l["terms"]))) for l in existing}
    merged, n_new = list(existing), 0
    for entry in candidates:
        key = (entry["class"], tuple(sorted(entry["terms"])))
        if key not in seen:
            merged.append(entry)
            seen.add(key)
            n_new += 1
    return merged[:LESSON_CAP], n_new


def match_lesson(question, lesson, stem_fn, stopwords):
    """Does the question share stemmed terms with the lesson?
    The application check for absence-annotation and hints."""
    import re
    qw = {stem_fn(w) for w in re.findall(r"[a-z0-9]+",
                                         question.lower())
          if w not in stopwords and len(w) >= 2}
    lt = {stem_fn(t) for t in lesson["terms"]}
    return bool(qw & lt)
