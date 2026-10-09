"""afterimage_api.py -- the product boundary (rung 2 of production
hardening). Thin wrappers over SessionStore with ONE design rule:
typed absence is IN the response schema. Every read returns either
records-with-provenance or a certified absence -- never an empty
payload the caller must interpret, never a silent miss.
"""
from afterimage_store import retrieve


class SessionAPI:
    def __init__(self, store):
        self.store = store

    def ask(self, session_id, question, k=3):
        """Read contract. Returns:
          status "records": {"records": [...], "n_above": int}
          status "absent":  {"note": <typed-absence line>,
                             "n_above": 0}"""
        records = self.store.get_records(session_id)
        ctx, n = retrieve(records, question, k=k)
        if n == 0:
            return {"status": "absent",
                    "note": ctx,
                    "n_above": 0}
        return {"status": "records",
                "records": ctx.split("\n"),
                "n_above": n}

    def history(self, session_id, key):
        """Eviction provenance for a key: the ghost rows that
        mention it, with needed_by links. The periphery is
        answerable."""
        return [g for g in self.store.get_ghost(session_id)
                if key.lower() in g["item"].lower()
                or g["item"].lower() in key.lower()]

    def lessons(self):
        return self.store.get_lessons()

    def health(self, session_id):
        """Crash-recovery status: latest sealed cycle + chain
        verdict. A store that cannot verify itself says so."""
        latest = self.store.latest_cycle(session_id)
        ok, broken = self.store.verify_chain(session_id)
        return {"latest_cycle": latest, "chain_ok": ok,
                "first_broken": broken}
