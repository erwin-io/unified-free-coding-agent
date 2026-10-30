import json
import unittest
from pathlib import Path

class GitHubPermissionGuardTests(unittest.TestCase):
    def test_no_direct_cloud_agent_merges(self):
        path = Path(__file__).resolve().parents[1] / "opencode.jsonc"
        config = json.loads(path.read_text(encoding="utf-8"))
        rules = config["permissions"]
        denied = [r["resource"] for r in rules
                  if r.get("action") == "shell" and r.get("effect") == "deny"]
        self.assertIn("git push *", denied)
        self.assertIn("gh pr merge*", denied)
        self.assertIn("gh repo delete*", denied)
        self.assertIn("gh auth token*", denied)
