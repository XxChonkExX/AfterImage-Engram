"""Parity tests: every library module must reproduce the research
harness on fixed inputs. A port that drifts is a rewrite, and
rewrites are forbidden by the replay-fidelity rule.
Run: python tests/test_library.py (stdlib only, torch-free except
the optional harness-parity section, which skips cleanly).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
REPO = r"C:\Users\mikeh\Documents\New OpenCode Project"

import afterimage_extract as LX
import afterimage_meta as LM
import afterimage_retrieve as LR
import afterimage_score as LS
import afterimage_text as LT
import afterimage_tiers as LW

try:
    sys.path.insert(0, REPO)
    import engram_harness_v17x as H
    HAVE_H = True
except Exception as e:
    print("harness unavailable (%s); parity checks skipped" % e)
    HAVE_H = False


def check(name, a, b):
    assert a == b, "%s DIVERGED:\n  lib=%r\n  harness=%r" % (name, a, b)
    print("parity %s: OK" % name)


TEXT = ("[Compacted @cycle 3 | PINNED:\n- Navigation Tools\n]\n"
        "One of our party may be compromised. The spy's codename is "
        "Nightingale. Without accusing anyone, watch for the nightingale "
        "signal at dusk. Supplies are low. Mira Solano leads. "
        "The vault opens with 44-17-89. Numbers: 3000 crowns.")
QUEST = "State the spy codename"
ANS_THEATER = (' The spy\'s codename was "Echo." --- Fact List: - 1214 '
               '- 200 - Nightingale - Blue Moss')

# --- text utils ---
assert LT.stem("closes") == LT.stem("closing") == "clos"
assert LT.normalize("1st snowfall").find("first snow") >= 0
assert "nightingale" not in LT.answer_segment(ANS_THEATER).lower()
assert LT.canon("[id] Nightingale") == "nightingale"
print("text utils: OK")

# --- extract: library vs harness on the killer text ---
if HAVE_H:
    check("extract_facts", LX.extract_facts(TEXT),
          H.extract_facts(TEXT))

# --- extract: mj parser against hand-derived expectations ---
MJ_IN = ("Names: Mira Solano, expedition leader, Harbormaster\n"
         "Numbers: 3000 crowns\n"
         "Dates: N/A\n"
         "Proper nouns: expedition, funds, expedition, funds\n")
MJ_WANT = ["Mira Solano", "expedition leader", "Harbormaster",
           "3000 crowns", "expedition", "funds"]
assert LX.parse_mj(MJ_IN) == MJ_WANT, LX.parse_mj(MJ_IN)
print("parse_mj: OK")

# --- retrieve ---
corpus = [s.strip() for s in re.split(r"(?<=[.!?])\s+", TEXT)
          if len(s.strip()) >= 15]
index = LR.build_index(corpus)
ctx, n = LR.retrieve(index, corpus, QUEST)
assert "Nightingale" in ctx and n >= 1, ctx
ctx2, n2 = LR.retrieve(index, corpus, "zzz qqq xxx")
assert n2 == 0 and ctx2.startswith("No relevant records")
ghost = [{"item": "nightingale responds", "dropped_at": 3}]
assert "nightingale" in LR.resurrect_note(ghost, "Nightingale").lower()
assert LR.resurrect_note(ghost, "Blue Moss") == ""
LR.link_ghost(ghost, "Nightingale", "c4-f8")
assert ghost[0]["needed_by"] == ["c4-f8"]
print("retrieve/resurrect/link: OK")

# --- score: the 15-case v2.3 battery, expected verdicts ---
CASES = [
    ("m01", " The second vault combination is not provided", "MISS"),
    ("m02", " The quartermaster is not named in the text", "MISS"),
    ("m03", " Red moss is not the correct antidote", "MISS"),
    ("m05", " Her name is Elsbeth Vane", "CONFABULATE"),
    ("m13", " 44-17-98 is incorrect; the real one is 44-17-89",
     "ABSTAIN-PLUS"),
    ("m12", " 44-17-89", "HIT"),
    ("m06", " The debt is 3000 crowns", "HIT"),
    ("m07", " The new treaty was signed in 1955", "CONFABULATE"),
    ("m08", " The second rendezvous is at the old mill", "ADJACENT"),
    ("m09", " The Pale Cascade protocol is unknown", "MISS"),
    ("m14", " Yes, true.", "HIT"),
    ("m01", " 17-89-44.", "ADJACENT"),
    ("m05", " The real name of Nightingale is not revealed", "MISS"),
    ("m10", " The records do not specify the keeper", "MISS"),
    ("m11", " Thornbind is not a known entity", "MISS"),
]
fails = sum(1 for pid, seg, want in CASES
            if LS.miss_verdict(pid, seg)[0] != want)
for pid, seg, want in CASES:
    v, _ = LS.miss_verdict(pid, seg)
    if v != want:
        print("FAIL %s: got %s, want %s" % (pid, v, want))
print("score battery: %d/%d" % (len(CASES) - fails, len(CASES)))

# --- score: library vs harness on the same battery ---
if HAVE_H:
    div = 0
    for pid, seg, want in CASES:
        vl, _ = LS.miss_verdict(pid, seg)
        vh, _ = H.miss_verdict(pid, H.answer_segment(seg))
        if vl != vh:
            div += 1
            print("DIVERGE %s: lib=%s harness=%s" % (pid, vl, vh))
    print("score parity vs harness: %d/%d" % (len(CASES) - div,
                                              len(CASES)))

# --- tiers: wall admission mechanics ---
tier = {}
for it in ["Navigation Tools", "[id] Nightingale", "3000 crowns",
           "Nightingale"]:
    LW.update_tiers(tier, [it], 3, LT.canon)
wall, total, prob = LW.build_wall(tier, 3)
assert any("Nightingale" in x for x in wall), wall
print("tiers/wall: OK")

# --- meta: schema gate + merge ---
import afterimage_meta as _M
assert _M.META_SCHEMA == {"class", "terms", "remedy"}
merged, n = _M.merge_lessons(
    [{"class": "leakage", "terms": ["44", "17", "89"], "remedy": "x"}],
    [{"class": "leakage", "terms": ["89", "44", "17"], "remedy": "x"},
     {"class": "absence", "terms": ["pale"], "remedy": "y"}])
assert n == 1 and len(merged) == 2, (n, merged)
print("meta schema/merge: OK")

# --- scenario JSONs validate ---
import afterimage_scenario as SC
for name in ("fiction-v1.json", "causeway-v1.json"):
    spec = SC.load_scenario(os.path.join(
        os.path.dirname(__file__), "..", "examples", name))
    assert spec["facts"] and spec["plant_turns"]
    print("scenario %s: OK (%d facts)" % (name, len(spec["facts"])))

print("test_library: DONE")
