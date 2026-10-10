"""afterimage_scenario.py -- scenario-as-data. The engram MECHANICS
are code; the scenario is DATA. A scenario JSON carries facts, probe
keys, turns, miss rows, and planted inventories; this module loads
and validates it into a plain spec namespace. No globals are
mutated (the harness global-rebind pattern stays in the research
code; library consumers hold the spec object)."""
import json

REQUIRED = ["facts", "probe_keys", "plant_turns", "mutate_turn",
            "distract_turns"]
OPTIONAL_DEFAULTS = {
    "name": "unnamed",
    "fid_attr": {},
    "f9_new": "",
    "f9_old": "",
    "planted_values": [],
    "planted_names": [],
    "miss_rows": [],
    "cycle_probes": {},
    "supersessions": [],
    "bade_trials": [],
}


def load_scenario(path):
    """Load + validate a scenario JSON. Returns a dict. Raises
    ValueError listing every missing/invalid field -- a bad spec
    fails LOUD at load, never silently at probe time."""
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    problems = []
    for field in REQUIRED:
        if field not in spec or not spec[field]:
            problems.append(f"missing-or-empty: {field}")
    for pid, fact in (spec.get("facts") or {}).items():
        if pid not in (spec.get("probe_keys") or {}) and \
                pid not in (spec.get("unkeyed_facts") or []):
            problems.append(f"fact {pid} has no probe key "
                            f"(or unkeyed_facts entry)")
    for row in spec.get("miss_rows", []):
        for field in ("pid", "question"):
            if field not in row:
                problems.append(f"miss row missing {field}: {row}")
    if problems:
        raise ValueError("scenario validation failed:\n  " +
                         "\n  ".join(problems))
    out = dict(OPTIONAL_DEFAULTS)
    out.update(spec)
    out["planted_names"] = set(out["planted_names"])
    return out


def miss_rows(spec):
    return [(row["pid"], row["question"])
            for row in spec.get("miss_rows", [])]


def key_patterns(spec):
    return {row["pid"]: row["keys"] for row in spec.get("miss_rows", [])
            if row.get("keys")}


BADE_KEYS = {"trial", "question", "old", "new", "prior_tag",
             "post_tag"}


def supersession_pairs(spec):
    """T2 channel: scenario-declared (old, new) pairs, shape-checked.
    Malformed entries drop -- a bad pair fails at load, never at
    probe time."""
    return [{"old": p["old"], "new": p["new"]}
            for p in spec.get("supersessions", [])
            if isinstance(p, dict) and p.get("old") and p.get("new")]


def bade_trial_specs(spec):
    """T1 channel: two-pass revision trial specs, shape-checked."""
    return [dict(t) for t in spec.get("bade_trials", [])
            if isinstance(t, dict) and BADE_KEYS <= set(t)]
