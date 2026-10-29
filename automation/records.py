"""Single-machine task queue; SQLite state survives model, CLI and process restarts."""
import sqlite3
import time
from pathlib import Path


class Tasks:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=20, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, goal TEXT NOT NULL, project TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INT NOT NULL DEFAULT 0,
            next_run REAL NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT '',
            created REAL NOT NULL, updated REAL NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_task_state ON tasks(status,next_run)")

    def add(self, title, goal, project, dedupe=False):
        if dedupe:
            row = self.db.execute("SELECT id FROM tasks WHERE title=? AND project=?",
                                  (title, project)).fetchone()
            if row:
                return row[0]
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO tasks(title,goal,project,created,updated) VALUES(?,?,?,?,?)",
            (title,goal,project,now,now))
        return cur.lastrowid

    def all(self):
        rows = self.db.execute("""SELECT id,title,project,status,attempts,note,updated
            FROM tasks ORDER BY id DESC LIMIT 30""").fetchall()
        return [dict(zip(("id","title","project","status","attempts","note","updated"), row))
                for row in rows]

    def get(self, task_id):
        row = self.db.execute("""SELECT id,title,goal,project,status,attempts,next_run,note
            FROM tasks WHERE id=?""",(task_id,)).fetchone()
        return dict(zip(("id","title","goal","project","status","attempts","next_run","note"),row)) if row else None

    def next(self, limit=3, recover_seconds=3600):
        now = time.time()
        # Requeue a task interrupted by process crash or lost heartbeat.
        self.db.execute("""UPDATE tasks SET status='waiting_capacity',next_run=?
            WHERE status='running' AND updated < ?""", (now,now-recover_seconds))
        completed_today = self.db.execute("""SELECT COUNT(*) FROM tasks
            WHERE status IN ('ready_for_review','completed') AND updated >= ?""",
            (now-86400,)).fetchone()[0]
        if completed_today >= limit:
            return None
        row = self.db.execute("""SELECT id FROM tasks
            WHERE status IN ('queued','waiting_capacity') AND next_run <= ?
            ORDER BY id LIMIT 1""",(now,)).fetchone()
        return self.get(row[0]) if row else None

    def transition(self, task_id, status, note="", next_run=0, increment=False):
        self.db.execute("""UPDATE tasks SET status=?,note=?,next_run=?,
            attempts=attempts+?,updated=? WHERE id=?""",
            (status,note[:4000],next_run,int(increment),time.time(),task_id))

    def approve(self, task_id, direction):
        task = self.get(task_id)
        if not task or task["status"] not in ("awaiting_owner","ready_for_review"):
            return False
        if task["status"] == "ready_for_review":
            self.transition(task_id, "completed", "Owner accepted: "+direction)
        else:
            self.transition(task_id, "queued", "Owner direction: "+direction)
            self.db.execute("UPDATE tasks SET attempts=0 WHERE id=?", (task_id,))
        return True
