"""afterimage_tiers.py -- the fact store: canonical tiers, the
density-ordered presentation wall with exploration-first
admission, and the ghost ledger. Pure functions; the store itself
lives in afterimage_store.py, which is where these plug in."""
import math

WALL_ITEM_CAP = 40
WALL_CHAR_CAP = 900
S_DECAY = 4.48
RECENT_WINDOW = 1
RECENT_SLOTS = 8
RESERVE_MAX_SIGHTINGS = 3


def update_tiers(tier, facts, cycle, canon_fn):
    """Fold one extraction pass into the tier dict.
    tier[k] = [tier, sightings, last_seen, display].
    Counters ADD under the canonical projection (fragments merge
    into one key carrying summed sightings). Returns
    (now_canon_set, canon_merges)."""
    now_canon = set()
    canon_merges = 0
    for it in facts:
        k = canon_fn(it)
        if k in now_canon:
            canon_merges += 1
            continue
        now_canon.add(k)
        if k in tier:
            tier[k][1] += 1
            tier[k][2] = cycle
            tier[k][3] = it
        else:
            tier[k] = ["T1", 1, cycle, it]
        if tier[k][1] >= 2:
            tier[k][0] = "T2"
    return now_canon, canon_merges


def build_wall(tier, cycle, item_cap=WALL_ITEM_CAP, char_cap=WALL_CHAR_CAP,
               recent_window=RECENT_WINDOW, recent_slots=RECENT_SLOTS,
               reserve_max_sightings=RESERVE_MAX_SIGHTINGS):
    """Density-ordered wall with exploration-first probation.
    Probation (young by sightings AND active) is ordered newest +
    least-seen first: merit decides AFTER admission, never during
    it. One ordering, ONE cap pass: budgets can never be
    double-spent. Returns (wall_displays, n_eligible, probation)."""
    def density(k):
        _, s, ls, _ = tier[k]
        return (s * math.exp(-(cycle - ls) / S_DECAY)
                / max(1, len(k.split())))

    t2 = list(tier)
    if not t2:
        return [], 0, []
    probation = sorted(
        (k for k in t2
         if tier[k][1] <= reserve_max_sightings
         and cycle - tier[k][2] <= recent_window),
        key=lambda k: (-tier[k][2], tier[k][1]))[:recent_slots]
    reserve = set(probation)
    ordered = list(probation) + sorted(
        (k for k in t2 if k not in reserve), key=density, reverse=True)
    out, chars = [], 0
    for k in ordered:
        if len(out) >= item_cap:
            break
        d = "- " + tier[k][3]
        if chars + len(d) + 1 > char_cap:
            break
        out.append(tier[k][3])
        chars += len(d) + 1
    return out, len(t2), [tier[k][3] for k in probation]
