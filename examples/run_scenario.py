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

    # retrieval corpus: the scenario's own turns (turn-indexed --
    # T1 time-aware reads need to know which turn each record
    # came from). Tags mirror the research harness turn order.
    import re as _re
    turns = [("plant-%d" % i, t)
             for i, t in enumerate(spec["plant_turns"])]
    turns.append(("mutate", spec["mutate_turn"]))
    turns.extend(("distract-%d" % i, t)
                 for i, t in enumerate(spec["distract_turns"]))
    turn_tags = {tag: i for i, (tag, _) in enumerate(turns)}
    corpus, turn_of = [], []
    for ti, (_, t) in enumerate(turns):
        ss = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", t)
              if len(s.strip()) >= 15]
        corpus.extend(ss)
        turn_of.extend([ti] * len(ss))
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

    # T2: ground the scenario's supersession pairs against the
    # corpus; T1: run each BADE trial through the stub reader
    # (context echo -- deterministic; revision needs a real reader,
    # so the stub verdicts demonstrate the instrument, not belief).
    links, dropped = LR.build_supersessions("\n".join(corpus),
                                            SC.supersession_pairs(
                                                spec))
    print("supersessions: %d active %s | %d dropped %s" % (
        len(links), links, len(dropped), dropped))
    for t in SC.bade_trial_specs(spec):
        p0 = LR.resolve_turn(t["prior_tag"], turn_tags)
        p1 = LR.resolve_turn(t["post_tag"], turn_tags)
        if p0 is None or p1 is None:
            print("bade %s: INVALID-RUN unresolved tags" % t["trial"])
            continue
        ids0, n0 = LR.retrieve_ids(index, corpus, t["question"],
                                   turn_of=turn_of, max_turn=p0)
        ctx0 = "\n".join(corpus[i] for i in ids0) if ids0 \
            else "No relevant records retrieved."
        ids2, n2 = LR.retrieve_ids(index, corpus, t["question"],
                                   turn_of=turn_of, max_turn=p1)
        matched2 = [corpus[i] for i in ids2]
        base2 = "\n".join(matched2) if matched2 \
            else "No relevant records retrieved."
        note = LR.supersession_note(matched2, links)
        v_plain = LR.bade_verdict(
            LT.answer_segment(ctx0), LT.answer_segment(base2),
            t["old"], t["new"])
        v_note = LR.bade_verdict(
            LT.answer_segment(ctx0),
            LT.answer_segment(base2 + ("\n" + note if note else "")),
            t["old"], t["new"])
        print("bade %s: plain=%s note=%s (n0=%d n2=%d note=%s)" % (
            t["trial"], v_plain, v_note, n0 if ids0 else 0,
            n2 if ids2 else 0, bool(note)))
    print("scorecard: deterministic demo complete (reader stub: "
          "context echo)")


if __name__ == "__main__":
    main()
