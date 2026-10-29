"""Small durable quota counter. Request metadata only; never store prompts, keys, or code."""
import sqlite3
import threading
import time
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS calls
            (ts REAL NOT NULL, provider TEXT NOT NULL, status INTEGER NOT NULL,
             latency_ms INTEGER NOT NULL, in_tokens INTEGER, out_tokens INTEGER)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_calls_ts ON calls(provider,ts)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS cooldown
            (provider TEXT PRIMARY KEY, until_ts REAL NOT NULL, reason TEXT NOT NULL)""")
        self.db.commit()

    def add(self, provider, status, latency_ms, in_tokens=None, out_tokens=None):
        with self.lock:
            self.db.execute("INSERT INTO calls VALUES (?,?,?,?,?,?)",
                            (time.time(), provider, status, latency_ms, in_tokens, out_tokens))
            self.db.commit()

    def counts(self, provider):
        with self.lock:
            now = time.time()
            return {k: self.db.execute(
                "SELECT COUNT(*) FROM calls WHERE provider=? AND ts >= ?",
                (provider, now - seconds)).fetchone()[0]
                for k, seconds in (("minute", 60), ("hour", 3600), ("day", 86400))}

    def cooldown(self, provider):
        with self.lock:
            row = self.db.execute(
                "SELECT until_ts,reason FROM cooldown WHERE provider=?", (provider,)).fetchone()
            if not row or row[0] <= time.time():
                return 0, ""
            return int(row[0]-time.time())+1, row[1]

    def block(self, provider, seconds, reason):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO cooldown VALUES(?,?,?)",
                            (provider, time.time()+seconds, reason[:80]))
            self.db.commit()

    def usage(self, provider):
        with self.lock:
            row = self.db.execute(
                "SELECT SUM(COALESCE(in_tokens,0)), SUM(COALESCE(out_tokens,0)) FROM calls WHERE provider=?",
                (provider,)).fetchone()
            return {"input_tokens_recorded": row[0] or 0, "output_tokens_recorded": row[1] or 0}
