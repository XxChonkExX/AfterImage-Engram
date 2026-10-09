"""afterimage_extract.py -- deterministic extraction. Strings,
never referents: regex catches strings; the model-judged pass (reader-
side, not here) catches referents. Extracted items are candidates --
the canonical projection merges them, tiers weigh them, the wall
shows the top. Pure functions, stdlib re + Counter only."""
import re
from collections import Counter


def extract_facts(text):
    # Never read our own scars: strip compaction marker lines before
    # extracting (marker boilerplate like "Compacted"/"Pinned" would
    # otherwise be pinned as identifiers).
    text = re.sub(r"^\[Compacted @cycle.*$", "", text,
                  flags=re.M)
    items, seen = [], set()

    def add(x):
        x = x.strip(" .,;:'\"")
        if len(x) >= 3 and x not in seen:
            seen.add(x)
            items.append(x)
    for m in re.finditer(r"\b\d[\d,\-]*(?:\.\d+)?\b", text):
        add(m.group(0))
    nums = [(int(m.group(1)), m.group(0))
            for m in re.finditer(r"(?<!\d)(\d{1,5})(?!\d)", text)]
    vals = sorted({v for v, _ in nums})
    # sequential runs of 3+: drop members (enumeration exhaust like
    # 1215-1219 dies here; isolated years like 1214 survive)
    seq_runs, cur = set(), []
    for v in vals:
        if cur and v == cur[-1] + 1:
            cur.append(v)
        else:
            if len(cur) >= 3:
                seq_runs.update(cur)
            cur = [v]
    if len(cur) >= 3:
        seq_runs.update(cur)
    items[:] = [x for x in items
                if not (x.isdigit() and int(x) in seq_runs)]
    months = ("January|February|March|April|May|June|July|August|September|"
              "October|November|December")
    for m in re.finditer(r"\b(?:%s)\b.{0,24}?\b\d{1,4}\b|\b\d{1,4}\b"
                         % months, text):
        add(m.group(0))
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[ ]+[A-Z][a-z]+){1,3})\b",
                         text):
        # space-only [ ]: \s+ crosses newlines and glues section
        # boundaries into fragments. Newlines never join identifiers.
        if m.group(1) not in ("The User", "The Assistant"):
            add(m.group(1))
    # IDENTIFIER TIER (case-vote repealed): any capitalized
    # mid-sentence word pins -- no vote, no count threshold.
    # Position + stoplist only; over-inclusion is absorbed by
    # tiers+ghost and stays visible in coverage.
    caps = Counter(re.findall(r"\b([A-Z][a-z]{3,})\b", text))
    stop = {"Without", "Describe", "Explain", "Detail", "Give", "Tell",
            "Walk", "Lay", "State", "Prior", "Meanwhile", "However",
            "Although", "Because", "Since", "While", "When", "Where",
            "Which", "What", "Also", "The", "User", "Assistant"}
    id_items, id_seen = [], set()
    for m in re.finditer(r"\b([A-Z][a-z]{3,})\b", text):
        w, s = m.group(1), m.start()
        if s == 0 or re.search(r"[.!?]\s+$", text[:s]):
            continue
        if w in stop or w in id_seen:
            continue
        id_seen.add(w)
        id_items.append((caps.get(w, 1), "[id] " + w))
    id_items = [x for _, x in sorted(id_items)]
    for m in re.finditer(r'"([^"]{3,80})"', text):
        add('"' + m.group(1) + '"')
    return items[:40] + id_items[:20]


def parse_mj(mj_raw):
    """Parse model-judged extraction output into identifier terms.
    Hardened against format half-obedience: labeled prefixes,
    comma-joined lists, N/A rows, and repetition loops (deduped).
    Identifiers are short terms: overlong items die here."""
    mj_items = []
    for ln in mj_raw.splitlines():
        ln = re.sub(r"^[\-\*\d\.\)\s]+", "", ln).strip()
        ln = re.sub(r"^[A-Za-z][A-Za-z ]{0,14}:\s*", "", ln)
        ln = re.sub(r"\s+", " ", ln)
        for seg in re.split(r"[,;]", ln):
            seg = seg.strip(" .;:'\"")
            if (len(seg) >= 3 and seg.upper() != "N/A"
                    and len(seg) <= 40):
                mj_items.append(seg)
    seen = set()
    return [x for x in mj_items
            if not (x.lower() in seen or seen.add(x.lower()))]
