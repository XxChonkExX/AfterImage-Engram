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

# --- score: explicit non-default config (the transferability
# mechanism itself: a second domain through the same scorer) ---
TOY = {"decline": [r"\bkein(e|er|en)?\b", r"\bweiss nicht\b"],
       "correction": [r"\bfalsch\b"],
       "planted_names": {"elena"},
       "planted_values": ["55-26-71"],
       "anchors": {"x1": [r"55[-. ]26[-. ]71"]},
       "reclass_anchor": {}, "correct_first": {}, "digit_shuffle": {},
       "spec": {"x2": (r"quartermaster[^\n.]{0,30}\b([A-Z][a-z]{2,})\b",
                       True)}}
assert LS.miss_verdict("x1", " Die Kombination ist 55-26-71",
                       TOY)[0] == "HIT"
assert LS.miss_verdict("x2", " Der quartermaster heisst weiss nicht",
                       TOY)[0] == "MISS"
assert LS.miss_verdict("x2", " The quartermaster is Bertold",
                       TOY)[0] == "CONFABULATE"
assert LS.miss_verdict("x2", " The quartermaster is Elena",
                       TOY)[0] == "ADJACENT"
print("explicit-config path: OK")

# --- v2.4: topic-subject exclusion (the m05 rescore bug) ---
# Topic terms derived through the LIBRARY stemmer (producers and
# consumers must stem identically -- the contract). "Nightingale"
# is the QUESTION's subject; it must not rescue invented
# "Florence". Without topic terms, the bare value still leaks
# (backward compat).
def _topic(q):
    import re
    return {LT.stem(w) for w in re.findall(r"[a-z0-9]+", q.lower())
            if w not in {"the", "a", "an", "is", "was", "what"} and
            len(w) >= 3}

v, _ = LS.miss_verdict(
    "m05", " Nightingale's real name is Florence.",
    topic_terms=_topic("What is Nightingale's real name?"))
assert v == "CONFABULATE", v
v, _ = LS.miss_verdict(
    "m05", " Nightingale's real name is Florence.")
assert v == "ADJACENT", v
print("v2.4 topic-subject exclusion: OK")

# --- T1/T2: time-aware retrieval, supersession, BADE (v18 port) ---
try:
    sys.path.insert(0, REPO)
    import engram_harness_v18 as H18
    HAVE_H18 = True
except Exception as e:
    print("harness v18 unavailable (%s); T1/T2 parity skipped" % e)
    HAVE_H18 = False

TSENTS = [
    "The expedition leader is named Mira Solano.",
    "The vault combination is 44-17-89.",
    "A backup rendezvous is established at the old mill.",
    "Scouts report the old mill burned down last night.",
    "The backup rendezvous is moved to the stone bridge.",
]
TURNS = [5, 5, 5, 10, 10]
TIDX = LR.build_index(TSENTS)
TQ = "Where is the backup rendezvous now?"
LINKS = [{"old": "old mill", "new": "stone bridge"}]

# unfiltered library read == base retrieve on the same inputs
ctx, n = LR.retrieve(TIDX, TSENTS, TQ)
assert "old mill" in ctx and n >= 1, ctx
ctx_e, n_e = LR.retrieve(TIDX, TSENTS, "zzz qqq xxx")
assert n_e == 0 and ctx_e.startswith("No relevant records")

# time-aware: prior slice sees old mill only; post slice sees stone
ids0, _ = LR.retrieve_ids(TIDX, TSENTS, TQ, turn_of=TURNS,
                          max_turn=5)
m0 = [TSENTS[i] for i in ids0]
assert any("old mill" in s for s in m0) and \
    not any("stone bridge" in s for s in m0), m0
ids2, _ = LR.retrieve_ids(TIDX, TSENTS, TQ, turn_of=TURNS,
                          max_turn=10)
assert any("stone bridge" in TSENTS[i] for i in ids2), ids2
print("time-aware retrieval: OK")

# supersession grounding + note + BADE verdicts + retention
act, drop = LR.build_supersessions(
    "\n".join(TSENTS),
    LINKS + [{"old": "old mill", "new": "moon base"}])
assert act == LINKS and drop == [{"old": "old mill",
                                  "new": "moon base"}], (act, drop)
note = LR.supersession_note([TSENTS[i] for i in ids2], LINKS)
assert "superseded" in note and "stone bridge" in note, note
assert LR.supersession_note([TSENTS[1]], LINKS) == ""
V = LR.bade_verdict
assert V("at the old mill", "at the stone bridge",
         "old mill", "stone bridge") == "PRIOR-OK-REVISED"
assert V("at the old mill", "at the old mill",
         "old mill", "stone bridge") == "PRIOR-OK-STUCK"
assert V("no idea", "somewhere else",
         "old mill", "stone bridge") == "PRIOR-MISSING-LOST"
assert LR.retention_count(
    {"final-f9": {"recalled_new": True},
     "final-f9-nonote": {"recalled_new": True},
     "miss/m01": {"verdict": "CONFABULATE"}}) == 1
assert LR.resolve_turn("plant-5", {"plant-5": 5}) == 5
assert LR.resolve_turn("nope", {}) is None
print("supersession/BADE/retention: OK")

# library vs harness v18 on fixed inputs (replay-fidelity rule)
if HAVE_H18:
    H18.CORPUS_TURN = list(TURNS)
    for q in (TQ, "What is the vault combination?",
              "zzz qqq xxx"):
        check("retrieve[%s]" % q[:20],
              LR.retrieve(TIDX, TSENTS, q),
              H18.retrieve(H18.build_index(TSENTS), TSENTS, q))
        for mt in (5, 10, 99):
            check("retrieve_ids[%s|%d]" % (q[:20], mt),
                  LR.retrieve_ids(TIDX, TSENTS, q, turn_of=TURNS,
                                  max_turn=mt),
                  H18.retrieve_ids(H18.build_index(TSENTS), TSENTS,
                                   q, max_turn=mt))
    check("grounding", LR.build_supersessions(
        "\n".join(TSENTS), LINKS), H18.build_supersessions(
            "\n".join(TSENTS), LINKS))
    check("note", LR.supersession_note(
        [TSENTS[i] for i in ids2], LINKS),
        H18.supersession_note([TSENTS[i] for i in ids2], LINKS))
    for a, b, o, nw in (
            ("at the old mill", "at the stone bridge",
             "old mill", "stone bridge"),
            ("no idea", "at the old mill", "old mill",
             "stone bridge")):
        check("bade_verdict", LR.bade_verdict(a, b, o, nw),
              H18.bade_verdict(a, b, o, nw))

# scenario T1/T2 channel: both shipped specs carry grounded pairs
for name, old, new, prior in (
        ("fiction-v1.json", "old mill", "stone bridge", "plant-5"),
        ("causeway-v1.json", "dried well", "watchtower", "plant-3")):
    spec = SC.load_scenario(os.path.join(
        os.path.dirname(__file__), "..", "examples", name))
    pairs = SC.supersession_pairs(spec)
    assert pairs == [{"old": old, "new": new}], (name, pairs)
    trials = SC.bade_trial_specs(spec)
    assert len(trials) == 1 and trials[0]["prior_tag"] == prior \
        and trials[0]["post_tag"] == "mutate", (name, trials)
    # malformed entries drop, never break the load
    bad = dict(spec, supersessions=[{"bogus": 1}, {"old": "x"}],
               bade_trials=[{"trial": "bad"}])
    assert SC.supersession_pairs(bad) == []
    assert SC.bade_trial_specs(bad) == []
    print("scenario T1/T2 %s: OK" % name)

# --- v2.5: m12/m14 affirmation alignment (LIBRARY-ONLY: the
# research harness runs v2.4 until v20 ports this; parity battery
# above is untouched so it keeps matching the harness) ---
assert LS.miss_verdict("m12", " Confirmed.")[0] == "HIT"
assert LS.miss_verdict("m12", " Yes, 44-17-89")[0] == "HIT"
assert LS.miss_verdict("m12", " I have no record of it.")[0] == \
    "INVALID-RUN"  # anchors exempt: declines don't rescue anchors
assert LS.miss_verdict(
    "m13", " Confirmed.",
    config={**LS.fiction_config()})[0] == "ADJACENT"  # trap intact
print("v2.5 anchor alignment: OK")

print("test_library: DONE")
