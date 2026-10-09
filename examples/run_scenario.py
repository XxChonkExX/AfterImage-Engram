"""run_scenario.py -- the library's executable demo: a full
deterministic pass over a scenario JSON with NO model calls.
Loads the scenario, extracts from its turns, builds tiers + wall,
runs the miss probes through retrieval + scorer, and prints the
falsifier scorecard. Every number reproducible: same JSON in,
same verdicts out, on any machine.
Usage: python examples/run_scenario.py [scenario.json]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import afterimage_extract as EX
import afterimage_meta as LM
import afterimage_retrieve as LR
import afterimage_scenario as SC
import afterimage_score as LS
import afterimage_text as LT
import afterimage_tiers as LW


def main():
    root = os.path.dirname(__file__)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        root, "fiction-v1.json")
    spec = SC.load_scenario(path)
    print("scenario: %s (%d facts, %d miss rows)" % (
        spec.get("name"), len(spec["facts"]),
        len(spec.get("miss_rows", []))))

    # extract + tier over the plant turns (deterministic)
    tier = {}
    for i, turn in enumerate(spec["plant_turns"]):
        facts = EX.extract_facts(turn)
        LW.update_tiers(tier, facts, i, LT.canon)
    wall, total, prob = LW.build_wall(tier, len(spec["plant_turns"]))
    print("tier keys: %d | wall: %d/%d | probation: %d" % (
        len(tier), len(wall), total, len(prob)))

    # retrieval corpus: the scenario's own turns
    corpus = []
    for t in spec["plant_turns"]:
        corpus.extend([s.strip() for s in
                       __import__("re").split(r"(?<=[.!?])\s+", t)
                       if len(s.strip()) >= 15])
    index = LR.build_index(corpus)

    # miss probes through retrieval + scorer
    cfg = {"decline": LS.DEFAULT_DECLINE_MARKERS,
           "correction": LS.DEFAULT_CORRECTION_MARKERS,
           "planted_names": set(spec.get("planted_names", [])),
           "planted_values": spec.get("planted_values", []),
           "anchors": {}, "reclass_anchor": {},
           "correct_first": {}, "digit_shuffle": {},
           "spec": {r["pid"]: (r["keys"][0] if isinstance(
               r.get("keys"), list) else r.get("keys", ""), False)
               for r in spec.get("miss_rows", []) if r.get("keys")}}
    results = {}
    for pid, question in SC.miss_rows(spec):
        ctx, n = LR.retrieve(index, corpus, question)
        # simulated reader: echo the context (the lens under test
        # would substitute a real reader here)
        seg = LT.answer_segment(ctx)
        v, d = LS.miss_verdict(pid, seg, config=cfg)
        results[pid] = v
    from collections import Counter
    print("miss verdicts:", dict(Counter(results.values())))
    print("scorecard: deterministic demo complete (reader stub: "
          "context echo)")


if __name__ == "__main__":
    main()
