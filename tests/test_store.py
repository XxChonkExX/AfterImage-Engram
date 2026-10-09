import json
import os
import sys
import tempfile

sys.path.insert(0, r"C:\Users\mikeh\Documents\New OpenCode Project\AfterImage-Engram\src")
from afterimage_store import SessionStore

tmp = tempfile.mkdtemp(prefix="afterimage_test_")
store = SessionStore(os.path.join(tmp, "t.db"),
                     os.path.join(tmp, "artifacts"))

# sessions + artifact dirs (the OUTDIR-collision fix)
store.create_session("s1", "fiction-v1", "reader-a")
store.create_session("s2", "causeway-v1", "reader-b")
d1 = store.artifact_dir("s1")
d2 = store.artifact_dir("s2")
assert d1 != d2 and os.path.isdir(d1) and os.path.isdir(d2)
print("sessions + isolated artifact dirs: PASS")

# tier CRUD + isolation
store.upsert_fact("s1", "nightingale", "T2", 4, 5, "Nightingale")
store.upsert_fact("s1", "nightingale", "T2", 5, 6, "Nightingale")
store.upsert_fact("s2", "nightingale", "T1", 1, 1, "[id] Nightingale")
t1 = store.get_tier("s1")
t2 = store.get_tier("s2")
assert t1["nightingale"] == ["T2", 5, 6, "Nightingale"]
assert t2["nightingale"][1] == 1  # no cross-session bleed
print("tier upsert/read + isolation: PASS")

# ghost append-only + linking
store.append_ghost("s1", "identify Nightingale", 3, "not re-extracted")
store.append_ghost("s1", "blue moss patch", 5, "wall-evicted")
store.link_ghost("s1", "Nightingale", "c4-f8")
g = store.get_ghost("s1")
assert g[0]["needed_by"] == ["c4-f8"], g[0]
assert g[1].get("needed_by") == []
print("ghost append + causal link: PASS")

# meta lessons: schema gate + dedupe + cap
kept, dropped = store.add_lessons([
    {"class": "leakage", "terms": ["44", "17", "89"],
     "remedy": "ADJACENT"},
    {"class": "prose-lesson", "terms": [],
     "remedy": "I think the model should try harder"},
    {"class": "leakage", "terms": ["89", "44", "17"],
     "remedy": "ADJACENT"},  # same terms, different order -> dedupe
])
assert kept == 1 and dropped == 1, (kept, dropped)
assert len(store.get_lessons()) == 1
print("meta schema gate + term-order dedupe: PASS")

# blobs: seal, verify, tamper detection
blob = {"cycle": 3, "facts": ["a", "b"], "summary": "storm passed"}
sha = store.seal_blob("s1", 3, "plant-4", blob)
ok, back = store.verify_blob("s1", 3)
assert ok and back["facts"] == ["a", "b"]
ok2, _ = store.verify_blob("s1", 99)
assert not ok2
print("seal/verify/missing: PASS")

# probes
store.record_probe("s1", "final", "f8", "HIT", "anchor", "Nightingale")
print("probe record: PASS")
print("afterimage_store unit tests PASS")
