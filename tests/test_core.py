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

    def test_retired_model_maps_to_current_free_flash(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY":"test",
                                     "GEMINI_MODEL":"gemini-2.5-flash",
                                     "OPENROUTER_API_KEY":"",
                                     "KILO_ENABLED":"false"}):
            self.assertEqual(providers()[0].model,"gemini-3.8-flash")

    def test_all_disabled(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY":"",
                                     "GEMINI_API_KEY":"",
                                     "KILO_ENABLED":"false"}):
            self.assertEqual(providers(),[])


class DurableState(unittest.TestCase):
    def test_usage_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"calls.sqlite3")
            with Store(path) as first:
                first.add("kilo",200,20,100,25)
            with Store(path) as reopened:
                self.assertEqual(reopened.counts("kilo")["hour"],1)
                self.assertEqual(reopened.usage("kilo")["input_tokens_recorded"],100)

    def test_task_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"tasks.sqlite3"
            with Tasks(path) as first:
                task_id=first.add("API","Repair test",folder)
            with Tasks(path) as second:
                second.transition(task_id,"waiting_capacity","No available model",100)
            with Tasks(path) as reopened:
                self.assertEqual(reopened.get(task_id)["status"],"waiting_capacity")

    def test_review_requires_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            with Tasks(Path(folder)/"tasks.sqlite3") as tasks:
                task_id=tasks.add("Review","Inspect patch",folder)
                self.assertFalse(tasks.approve(task_id,"Go"))
                tasks.transition(task_id,"awaiting_owner")
                self.assertTrue(tasks.approve(task_id,"Approach B"))
                self.assertEqual(tasks.get(task_id)["status"],"queued")

if __name__=="__main__":
    unittest.main()
