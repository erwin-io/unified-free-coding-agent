"""Review gate, per-project backlog and no-unattended-main editing regression."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from automation.review import ensure_task_branch, feature_branch, write_review_packet
from automation.records import Tasks

def git(path, *args):
    result=subprocess.run(["git",*args],cwd=path,check=True,capture_output=True,
                          text=True,timeout=15)
    return result.stdout.strip()

class ReviewTests(unittest.TestCase):
    def git_project(self, path):
        git(path,"init","-b","main")
        (path/"README.md").write_text("baseline\n", encoding="utf-8")
        git(path,"add","README.md")
        git(path,"-c","user.name=Test","-c","user.email=test@invalid.local",
            "commit","-m","baseline")

    def test_branch_creation_preserves_uncommitted_work(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            self.git_project(path)
            (path/"README.md").write_text("work in progress\n",encoding="utf-8")
            task={"id":1,"source_id":"TASK-001","title":"Image upload"}
            self.assertEqual(ensure_task_branch(path,task),"agent/task-001")
            self.assertEqual(git(path,"branch","--show-current"),"agent/task-001")
            self.assertEqual((path/"README.md").read_text(),"work in progress\n")
            self.assertEqual(ensure_task_branch(path,task),"agent/task-001")

    def test_refuse_unknown_branch_and_never_switch_to_main(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            self.git_project(path)
            git(path,"switch","-c","owner/other-feature")
            with self.assertRaisesRegex(RuntimeError,"Expected"):
                ensure_task_branch(path,{"id":2,"source_id":"TASK-002"})

    def test_review_packet_contains_project_specific_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            self.git_project(path)
            folder=path/".agent"
            folder.mkdir()
            (folder/"CHECKLIST.md").write_text("- [ ] TASK-001 file upload\n")
            (folder/"TEST_EVIDENCE.md").write_text("Test command: npm test\nExit code: 0\n")
            (path/"README.md").write_text("changed\n")
            packet=write_review_packet(path,{"id":1,"title":"File upload"})
            result=packet.read_text(encoding="utf-8")
            self.assertIn("TASK-001 file upload",result)
            self.assertIn("Exit code: 0",result)
            self.assertIn("README.md",result)
            self.assertIn("NOT APPROVED",result)
            self.assertIn("Decision: PENDING",result)

    def test_review_gate_and_explicit_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            with Tasks(Path(directory)/"state.sqlite") as db:
                t1=db.add("Upload","Build upload API",directory)
                t2=db.add("Gallery","Add gallery",directory)
                db.transition(t1,"ready_for_review")
                self.assertEqual(db.review_pending(directory),t1)
                self.assertFalse(db.approve(t1,"Looks good"))
                self.assertTrue(db.approve(t1,"APPROVED"))
                self.assertEqual(db.get(t1)["status"],"completed")
                self.assertIsNone(db.review_pending(directory))
                self.assertEqual(db.get(t2)["status"],"queued")
