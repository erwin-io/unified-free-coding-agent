"""Project backlog, state migration and terminal command verification."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from automation.backlog import approved_items, sync_approved_tasks
from automation.records import Tasks
from automation.validation import discover, validate_project


class TaskSource(unittest.TestCase):
    def test_approved_import_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/".agent").mkdir()
            (path/".agent"/"BACKLOG.md").write_text(
                "## TASK-101: Fix login\nStatus: approved\nAcceptance:\n- Login test passes\n"
                "## TASK-102: Payment change\nStatus: draft\n", encoding="utf-8")
            with Tasks(path/"queue.sqlite3") as tasks:
                self.assertEqual(sync_approved_tasks(path,tasks),1)
                self.assertEqual(sync_approved_tasks(path,tasks),0)
                self.assertEqual(len(tasks.all()),1)
                self.assertIn("Login test",tasks.get(tasks.all()[0]["id"])["goal"])

    def test_duplicate_task_ids_block_import(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/".agent").mkdir()
            (path/".agent"/"BACKLOG.md").write_text(
                "## TASK-1: A\nStatus: approved\n"
                "## TASK-1: B\nStatus: approved\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                approved_items(path)

    def test_migration_existing_queue(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"queue.db"
            conn=sqlite3.connect(db)
            conn.execute("""CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, goal TEXT NOT NULL, project TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                attempts INT NOT NULL DEFAULT 0,
                next_run REAL NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                created REAL NOT NULL, updated REAL NOT NULL)""")
            conn.commit()
            conn.close()
            with Tasks(db) as tasks:
                self.assertEqual(tasks.get(tasks.add("A","B",d,source_id="TASK-1"))["status"],"queued")


class ProjectValidation(unittest.TestCase):
    def test_node_test_and_lint(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/"package.json").write_text(json.dumps(
                {"scripts":{"test":"vitest run","lint":"eslint .","build":"vite build"}}))
            self.assertEqual([cmd[-1] for cmd in discover(path)],["test","lint"])

    def test_placeholder_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/"package.json").write_text(json.dumps(
                {"scripts":{"test":"echo 'Error: no test specified' && exit 1"}}))
            self.assertFalse(validate_project(path).passed)

    def test_project_script_success(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/".agent").mkdir()
            (path/"verify.py").write_text("print('VERIFY_OK')\n",encoding="utf-8")
            (path/".agent"/"validation.json").write_text(json.dumps(
                {"commands":[[sys.executable,"verify.py"]]}),encoding="utf-8")
            result=validate_project(path)
            self.assertTrue(result.passed)
            self.assertIn("VERIFY_OK",(path/".agent"/"TEST_EVIDENCE.md").read_text())

    def test_project_script_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/".agent").mkdir()
            (path/"verify.py").write_text("raise SystemExit(2)\n",encoding="utf-8")
            (path/".agent"/"validation.json").write_text(json.dumps(
                {"commands":[[sys.executable,"verify.py"]]}),encoding="utf-8")
            self.assertFalse(validate_project(path).passed)
            self.assertIn("Exit code: 2",(path/".agent"/"TEST_EVIDENCE.md").read_text())

    def test_no_tests_is_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            result=validate_project(Path(d))
            self.assertFalse(result.passed)
            self.assertEqual(result.commands,())


if __name__=="__main__":
    unittest.main()
