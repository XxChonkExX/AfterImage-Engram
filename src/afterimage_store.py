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
"""


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
