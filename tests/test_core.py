import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from automation.records import Tasks
from router.config import providers
from router.store import Store


class SafeRouting(unittest.TestCase):
    def test_nonfree_model_excluded(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"dummy",
                                     "GEMINI_MODEL":"paid-model",
                                     "OPENROUTER_API_KEY":"dummy",
                                     "KILO_ENABLED":"true"}):
            choices=providers()
            self.assertNotIn("gemini",[p.name for p in choices])
            self.assertEqual({p.model for p in choices},{"kilo-auto/free","openrouter/free"})

    def test_all_disabled(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY":"",
                                     "GEMINI_API_KEY":"",
                                     "KILO_ENABLED":"false"}):
            self.assertEqual(providers(),[])


class DurableState(unittest.TestCase):
    def test_usage_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"calls.sqlite3")
            Store(path).add("kilo",200,20,100,25)
            reopened=Store(path)
            self.assertEqual(reopened.counts("kilo")["hour"],1)
            self.assertEqual(reopened.usage("kilo")["input_tokens_recorded"],100)

    def test_task_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"tasks.sqlite3"
            task_id=Tasks(path).add("API","Repair test",folder)
            Tasks(path).transition(task_id,"waiting_capacity","No available model",100)
            self.assertEqual(Tasks(path).get(task_id)["status"],"waiting_capacity")

    def test_review_requires_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            tasks=Tasks(Path(folder)/"tasks.sqlite3")
            task_id=tasks.add("Review","Inspect patch",folder)
            self.assertFalse(tasks.approve(task_id,"Go"))
            tasks.transition(task_id,"awaiting_owner")
            self.assertTrue(tasks.approve(task_id,"Approach B"))
            self.assertEqual(tasks.get(task_id)["status"],"queued")


if __name__=="__main__":
    unittest.main()
