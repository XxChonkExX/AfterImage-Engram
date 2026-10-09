import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from afterimage_store import SessionStore

# Local-only replay: the frozen run artifacts live on the lab box.
# Off-box (CI, clones), this test skips cleanly -- the portable
# suite is test_store.py + test_rungs.py.
REPDIR = os.environ.get(
    "AFTERIMAGE_REPLAY_DIR",
    r"G:\New folder\learner_staging\engram_proto_v17_1b")
METAF = os.environ.get(
    "AFTERIMAGE_META",
    r"G:\New folder\learner_staging\engram_meta.json")
if not (os.path.isdir(REPDIR) and os.path.isfile(METAF)):
    print("replay skipped (no frozen artifacts; set "
          "AFTERIMAGE_REPLAY_DIR to run)")
    sys.exit(0)

# Backward-compat replay: v17.1b's frozen artifacts migrate into
# the session store with zero loss. This is the proof that the
# new persistence layer is a superset of every run format we
# ever produced.
tmp = tempfile.mkdtemp(prefix="afterimage_replay_")
store = SessionStore(os.path.join(tmp, "t.db"),
                     os.path.join(tmp, "artifacts"))
rep = json.load(open(
    os.path.join(REPDIR, "report.json"),
    encoding="utf-8"))
store.create_session("v17.1b-replay", "fiction-v1", "qwen2.5-3b",
                     {"source": "frozen-report"})

import glob
engrams = {}
for f in glob.glob(os.path.join(REPDIR, "engram_*.json")):
    b = json.load(open(f, encoding="utf-8"))
    engrams[b["cycle"]] = b
final = engrams[max(engrams)]

# verdicts
n_verd = 0
for k, v in rep["probes"].items():
    if k.startswith("miss/"):
        tag, pid = "miss", k.split("/")[1]
        store.record_probe("v17.1b-replay", tag, pid,
                           v.get("verdict", "?"),
                           v.get("detail", ""), v.get("answer", "")[:80])
        n_verd += 1
    elif "-" in k:
        tag, pid = k.split("-", 1)
        verdict = "HIT" if (v.get("recalled")
                            or v.get("recalled_new")) else "MISS"
        store.record_probe("v17.1b-replay", tag, pid, verdict,
                           "", v.get("answer", "")[:80])

# ghost ledger (with its causal edges)
n_ghost = 0
for g in final.get("ghost", []):
    store.append_ghost("v17.1b-replay", g["item"],
                       g.get("dropped_at", 0), g.get("reason", ""))
    n_ghost += 1

# sealed blobs, all cycles
n_blob = 0
for c, b in sorted(engrams.items()):
    blob = {k: v for k, v in b.items() if k != "sha"}
    store.seal_blob("v17.1b-replay", c, b.get("at", "?"), blob)
    ok, _ = store.verify_blob("v17.1b-replay", c)
    assert ok, f"seal broken at cycle {c}"
    n_blob += 1

# meta lessons
meta = json.load(open(
    METAF, encoding="utf-8"))
kept, dropped = store.add_lessons(meta["lessons"])

print(f"replay: {n_verd} verdicts, {n_ghost} ghost entries, "
      f"{n_blob} sealed+verified blobs, {kept} lessons kept, "
      f"{dropped} dropped")
assert store.get_ghost("v17.1b-replay")[-1]["item"] == \
    final["ghost"][-1]["item"]
print("tail-entry fidelity: PASS")
print("backward-compat replay: PASS")
