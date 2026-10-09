import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from afterimage_store import SessionStore
from afterimage_api import SessionAPI

tmp = tempfile.mkdtemp(prefix="afterimage_rungs_")
store = SessionStore(os.path.join(tmp, "t.db"),
                     os.path.join(tmp, "artifacts"))
api = SessionAPI(store)

# ---- rung 2: read contract ----
store.create_session("s1", "fiction-v1", "reader-a")
store.add_records("s1", ["The spy's codename is Nightingale.",
                         "The vault opens with 44-17-89.",
                         "Supplies are low."])
r = api.ask("s1", "What is the spy's codename?")
assert r["status"] == "records" and any("Nightingale" in x
                                        for x in r["records"]), r
r2 = api.ask("s1", "zzz qqq absent content xxx")
assert r2["status"] == "absent" and "No relevant records" in r2["note"]
print("read contract (records/typed-absence): PASS")

# ---- rung 3: crash recovery ----
store.seal_blob("s1", 1, "plant-0", {"facts": ["a"]})
store.seal_blob("s1", 2, "plant-3", {"facts": ["a", "b"]})
h = api.health("s1")
assert h == {"latest_cycle": 2, "chain_ok": True,
             "first_broken": None}, h
# tamper cycle 1 directly, verify names the broken cycle
import sqlite3
con = sqlite3.connect(os.path.join(tmp, "t.db"))
con.execute("UPDATE blobs SET blob_json='{\"facts\":[\"X\"]}' "
            "WHERE session_id='s1' AND cycle=1")
con.commit()
con.close()
h2 = api.health("s1")
assert h2["chain_ok"] is False and h2["first_broken"] == 1, h2
print("crash recovery (tamper detected at cycle 1): PASS")

# ---- rung 4: multi-agent, disagreement-as-new-file ----
store.attach("ops", "agent-a", "writer")
store.attach("ops", "agent-b", "writer")
store.attach("ops", "auditor", "reader")
st, _ = store.write_claim("ops", "agent-a", "rendezvous",
                          "the lighthouse")
assert st == "kept"
st, _ = store.write_claim("ops", "agent-b", "rendezvous",
                          "the old mill")
assert st == "contested", st  # disagreement flagged, both kept
view = store.read_claims("ops", "auditor")
assert view["rendezvous"]["contested"] is True
assert view["rendezvous"]["claims"] == {
    "agent-a": "the lighthouse", "agent-b": "the old mill"}
# same-agent rewrite: latest wins for that agent, no new conflict
st, _ = store.write_claim("ops", "agent-a", "rendezvous",
                          "the lighthouse")
assert st == "kept"
# reader denied write
try:
    store.write_claim("ops", "auditor", "x", "y")
    raise AssertionError("reader wrote!")
except PermissionError:
    pass
try:
    store.read_claims("ops", "stranger")
    raise AssertionError("stranger read!")
except PermissionError:
    pass
print("multi-agent (disagreement kept, ACLs enforced): PASS")
print("rungs 2-4 unit tests PASS")
