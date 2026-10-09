"""afterimage_store.py -- session-isolated persistence layer (rung 1
of production hardening). SQLite + WAL: one session per namespace,
locks per session, hash-chained blobs, the ghost ledger and the
meta-namespace as tables. Design rules, enforced in code:
  - artifact dirs are per-session (the OUTDIR-collision class dies
    here: two sessions can never share a path);
  - blobs carry content-minus-sha, verified on read (the v8 lesson);
  - ghost entries are append-only (eviction provenance is never
    rewritten);
  - meta lessons are schema-gated on load (prose lessons dropped
    on the record).
No model, no reader, no torch: pure stdlib. Print nothing.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time

META_SCHEMA = {"class", "terms", "remedy"}
LESSON_CAP = 50

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  created_utc REAL NOT NULL,
  scenario TEXT NOT NULL,
  reader TEXT NOT NULL,
  config_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS tier (
  session_id TEXT NOT NULL,
  canon_key TEXT NOT NULL,
  tier TEXT NOT NULL CHECK (tier IN ('T1','T2')),
  sightings INTEGER NOT NULL DEFAULT 1,
  last_seen INTEGER NOT NULL DEFAULT 0,
  display TEXT NOT NULL,
  PRIMARY KEY (session_id, canon_key)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS ghost (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  item TEXT NOT NULL,
  dropped_at INTEGER NOT NULL,
  reason TEXT NOT NULL,
  needed_by_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ghost_sess ON ghost(session_id);
CREATE TABLE IF NOT EXISTS meta_lessons (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  class TEXT NOT NULL,
  terms_json TEXT NOT NULL,
  remedy TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS blobs (
  session_id TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  tag TEXT NOT NULL,
  blob_json TEXT NOT NULL,
  sha TEXT NOT NULL,
  PRIMARY KEY (session_id, cycle)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS probes (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  pid TEXT NOT NULL,
  verdict TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  answer TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS probes_sess ON probes(session_id);
CREATE TABLE IF NOT EXISTS records (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_sess ON records(session_id);
CREATE TABLE IF NOT EXISTS claims (
  rowid INTEGER PRIMARY KEY AUTOINCREMENT,
  namespace TEXT NOT NULL,
  canon_key TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  display TEXT NOT NULL,
  created_utc REAL NOT NULL,
  contested INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS claims_ns ON claims(namespace, canon_key);
CREATE TABLE IF NOT EXISTS acl (
  namespace TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('reader', 'writer')),
  PRIMARY KEY (namespace, agent_id)
) WITHOUT ROWID;
"""

STOPWORDS = {"the", "a", "an", "is", "was", "are", "were", "what",
             "when", "where", "who", "how", "does", "did", "do",
             "of", "at", "in", "on", "to", "for", "and", "or",
             "say", "says", "state", "give", "confirm", "true"}


def stem(w):
    for _ in range(2):
        for suf in ("ing", "ed", "er", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        else:
            break
    return w


def retrieve(records, question, k=3, theta=1):
    """Answer-time retrieval over stored records. PURE. Returns
    (context_block, n_above_theta): top-k records above theta, or
    the typed-absence line. Absence is IN the contract."""
    import re
    qwords = {stem(w) for w in re.findall(r"[a-z0-9]+",
                                          question.lower())
              if w not in STOPWORDS and len(w) >= 2}
    hits = {}
    for i, s in enumerate(records):
        lwords = {stem(w) for w in re.findall(r"[a-z0-9]+", s.lower())
                  if w not in STOPWORDS and len(w) >= 2}
        score = len(qwords & lwords)
        if score >= theta:
            hits[i] = score
    if not hits:
        return "No relevant records retrieved.", 0
    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    top = [records[i] for i, s in ranked[:k] if s >= theta]
    if not top:
        return "No relevant records retrieved.", 0
    return "\n".join(top), len(hits)


class SessionStore:
    def __init__(self, db_path, artifact_root):
        self.db_path = db_path
        self.artifact_root = artifact_root
        os.makedirs(artifact_root, exist_ok=True)
        self._locks = {}
        self._locks_guard = threading.Lock()
        con = self._connect()
        try:
            con.executescript(_SCHEMA)
            con.execute("PRAGMA journal_mode=WAL")
            con.commit()
        finally:
            con.close()

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=30.0,
                              check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _lock(self, session_id):
        with self._locks_guard:
            return self._locks.setdefault(session_id,
                                          threading.Lock())

    # ---- sessions ----
    def create_session(self, session_id, scenario, reader, config=None):
        con = self._connect()
        try:
            with self._lock(session_id):
                con.execute(
                    "INSERT OR REPLACE INTO sessions "
                    "(session_id, created_utc, scenario, reader, "
                    "config_json) VALUES (?,?,?,?,?)",
                    (session_id, time.time(), scenario, reader,
                     json.dumps(config or {})))
                con.commit()
        finally:
            con.close()
        os.makedirs(self.artifact_dir(session_id), exist_ok=True)
        return session_id

    def artifact_dir(self, session_id):
        safe = "".join(c if (c.isalnum() or c in "-_") else "_"
                       for c in session_id)
        return os.path.join(self.artifact_root, safe)

    # ---- tier ----
    def upsert_fact(self, session_id, key, tier, sightings, last_seen,
                    display):
        con = self._connect()
        try:
            with self._lock(session_id):
                con.execute(
                    "INSERT INTO tier (session_id, canon_key, tier, "
                    "sightings, last_seen, display) VALUES (?,?,?,?,?,?)"
                    " ON CONFLICT(session_id, canon_key) DO UPDATE SET "
                    "tier=excluded.tier, sightings=excluded.sightings, "
                    "last_seen=excluded.last_seen, "
                    "display=excluded.display",
                    (session_id, key, tier, sightings, last_seen,
                     display))
                con.commit()
        finally:
            con.close()

    def get_tier(self, session_id):
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT canon_key, tier, sightings, last_seen, display"
                " FROM tier WHERE session_id=?", (session_id,)).fetchall()
        finally:
            con.close()
        return {k: [t, s, ls, d] for k, t, s, ls, d in rows}

    # ---- ghost (append-only) ----
    def append_ghost(self, session_id, item, dropped_at, reason):
        con = self._connect()
        try:
            with self._lock(session_id):
                con.execute(
                    "INSERT INTO ghost (session_id, item, dropped_at, "
                    "reason) VALUES (?,?,?,?)",
                    (session_id, item, dropped_at, reason))
                con.commit()
        finally:
            con.close()

    def link_ghost(self, session_id, text, probe_id):
        tl = text.lower()
        con = self._connect()
        try:
            with self._lock(session_id):
                rows = con.execute(
                    "SELECT rowid, item, needed_by_json FROM ghost "
                    "WHERE session_id=?", (session_id,)).fetchall()
                for rid, item, nbj in rows:
                    it = (item or "").lower()
                    if tl and it and (tl in it or it in tl):
                        nb = json.loads(nbj)
                        if probe_id not in nb:
                            nb.append(probe_id)
                            con.execute(
                                "UPDATE ghost SET needed_by_json=? "
                                "WHERE rowid=?",
                                (json.dumps(nb), rid))
                con.commit()
        finally:
            con.close()

    def get_ghost(self, session_id):
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT item, dropped_at, reason, needed_by_json "
                "FROM ghost WHERE session_id=? ORDER BY rowid",
                (session_id,)).fetchall()
        finally:
            con.close()
        return [{"item": it, "dropped_at": da, "reason": r,
                 "needed_by": json.loads(n)} for it, da, r, n in rows]

    # ---- meta lessons (global namespace, schema-gated) ----
    def get_lessons(self):
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT class, terms_json, remedy, hits FROM meta_lessons"
                " ORDER BY rowid LIMIT ?", (LESSON_CAP,)).fetchall()
        finally:
            con.close()
        return [{"class": c, "terms": json.loads(t), "remedy": r,
                 "hits": h} for c, t, r, h in rows]

    def add_lessons(self, lessons):
        """Returns (kept, dropped); schema-invalid entries are
        dropped on the record, never trusted."""
        kept = dropped = 0
        con = self._connect()
        try:
            with self._lock("__meta__"):
                existing = {(r[0], r[1]) for r in con.execute(
                    "SELECT class, terms_json FROM meta_lessons")}
                for entry in lessons:
                    if not (META_SCHEMA.issubset(entry)
                            and isinstance(entry.get("terms"), list)
                            and entry["terms"]):
                        dropped += 1
                        continue
                    key = (entry["class"],
                           json.dumps(sorted(entry["terms"])))
                    if key in existing:
                        continue
                    con.execute(
                        "INSERT INTO meta_lessons (class, terms_json, "
                        "remedy, hits) VALUES (?,?,?,?)",
                        (entry["class"],
                         json.dumps(sorted(entry["terms"])),
                         entry["remedy"], entry.get("hits", 0)))
                    existing.add(key)
                    kept += 1
                # cap: retire oldest-zero-hit rows first
                over = con.execute(
                    "SELECT COUNT(*) FROM meta_lessons").fetchone()[0]
                if over > LESSON_CAP:
                    con.execute(
                        "DELETE FROM meta_lessons WHERE rowid IN "
                        "(SELECT rowid FROM meta_lessons ORDER BY hits "
                        "ASC, rowid ASC LIMIT ?)", (over - LESSON_CAP,))
                con.commit()
        finally:
            con.close()
        return kept, dropped

    # ---- blobs (sealed, hash-verified on read) ----
    @staticmethod
    def _hash(blob):
        raw = json.dumps(blob, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    def seal_blob(self, session_id, cycle, tag, blob):
        blob = dict(blob)
        sha = self._hash(blob)
        con = self._connect()
        try:
            with self._lock(session_id):
                con.execute(
                    "INSERT OR REPLACE INTO blobs (session_id, cycle, "
                    "tag, blob_json, sha) VALUES (?,?,?,?,?)",
                    (session_id, cycle, tag,
                     json.dumps(blob, sort_keys=True), sha))
                con.commit()
        finally:
            con.close()
        return sha

    def verify_blob(self, session_id, cycle):
        """Returns (ok, blob). A failed hash is a hard failure --
        the seal means something."""
        con = self._connect()
        try:
            row = con.execute(
                "SELECT blob_json, sha FROM blobs WHERE session_id=? "
                "AND cycle=?", (session_id, cycle)).fetchone()
        finally:
            con.close()
        if row is None:
            return False, None
        blob = json.loads(row[0])
        return self._hash(blob) == row[1], blob

    # ---- probes ----
    def record_probe(self, session_id, tag, pid, verdict, detail="",
                     answer=""):
        con = self._connect()
        try:
            with self._lock(session_id):
                con.execute(
                    "INSERT INTO probes (session_id, tag, pid, verdict,"
                    " detail, answer) VALUES (?,?,?,?,?,?)",
                    (session_id, tag, pid, verdict, detail, answer))
                con.commit()
        finally:
            con.close()

    # ---- records (the retrieval corpus) ----
    def add_records(self, session_id, texts):
        con = self._connect()
        try:
            with self._lock(session_id):
                for t in texts:
                    con.execute(
                        "INSERT INTO records (session_id, text) "
                        "VALUES (?,?)", (session_id, t))
                con.commit()
        finally:
            con.close()

    def get_records(self, session_id):
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT text FROM records WHERE session_id=? "
                "ORDER BY rowid", (session_id,)).fetchall()
        finally:
            con.close()
        return [r[0] for r in rows]

    # ---- crash recovery: chain verification ----
    def latest_cycle(self, session_id):
        con = self._connect()
        try:
            row = con.execute(
                "SELECT MAX(cycle) FROM blobs WHERE session_id=?",
                (session_id,)).fetchone()
        finally:
            con.close()
        return row[0]

    def verify_chain(self, session_id):
        """Crash-recovery read: verify every sealed blob in cycle
        order. Returns (ok, first_broken_cycle_or_None). A break is
        bounded (named cycle), never silent."""
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT cycle, blob_json, sha FROM blobs "
                "WHERE session_id=? ORDER BY cycle",
                (session_id,)).fetchall()
        finally:
            con.close()
        for cyc, blob_json, sha in rows:
            blob = json.loads(blob_json)
            if self._hash(blob) != sha:
                return False, cyc
        return True, None

    # ---- multi-agent: namespaces, ACLs, disagreement-as-new-file --
    def attach(self, namespace, agent_id, role="reader"):
        if role not in ("reader", "writer"):
            raise ValueError("role must be reader|writer")
        con = self._connect()
        try:
            con.execute(
                "INSERT OR REPLACE INTO acl (namespace, agent_id, "
                "role) VALUES (?,?,?)", (namespace, agent_id, role))
            con.commit()
        finally:
            con.close()

    def _role(self, namespace, agent_id):
        con = self._connect()
        try:
            row = con.execute(
                "SELECT role FROM acl WHERE namespace=? AND agent_id=?",
                (namespace, agent_id)).fetchone()
        finally:
            con.close()
        return row[0] if row else None

    def write_claim(self, namespace, agent_id, key, display):
        """Disagreement-as-new-file: a writer's claim is ALWAYS an
        insert, never an overwrite. If another agent already holds a
        different display for the same key, both persist and the new
        row is flagged contested. Returns (status, rowid) with status
        in {kept, contested}."""
        if self._role(namespace, agent_id) != "writer":
            raise PermissionError(
                f"{agent_id} is not a writer on {namespace}")
        con = self._connect()
        try:
            with self._lock("ns:" + namespace):
                others = con.execute(
                    "SELECT display FROM claims WHERE namespace=? "
                    "AND canon_key=? AND agent_id!=? AND contested=0",
                    (namespace, key, agent_id)).fetchall()
                contested = any(d[0] != display for d in others)
                cur = con.execute(
                    "INSERT INTO claims (namespace, canon_key, "
                    "agent_id, display, created_utc, contested) "
                    "VALUES (?,?,?,?,?,?)",
                    (namespace, key, agent_id, display, time.time(),
                     1 if contested else 0))
                con.commit()
                return ("contested" if contested else "kept",
                        cur.lastrowid)
        finally:
            con.close()

    def read_claims(self, namespace, agent_id):
        """Merged view: latest claim per (key, agent); contested=True
        when agents disagree on a key."""
        if self._role(namespace, agent_id) not in ("reader",
                                                   "writer"):
            raise PermissionError(
                f"{agent_id} has no access to {namespace}")
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT canon_key, agent_id, display, contested "
                "FROM claims WHERE namespace=? ORDER BY rowid",
                (namespace,)).fetchall()
        finally:
            con.close()
        merged = {}
        for key, ag, disp, cont in rows:
            slot = merged.setdefault(key, {})
            slot[ag] = disp
        out = {}
        for key, slot in merged.items():
            displays = set(slot.values())
            out[key] = {"claims": dict(slot),
                        "contested": len(displays) > 1}
        return out
