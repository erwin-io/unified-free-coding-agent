import json
import unittest
from pathlib import Path

class PluginConfigTests(unittest.TestCase):
    def test_capacity_plugin_is_loaded_from_opencode_config(self):
        config=Path(__file__).resolve().parents[1] / "opencode.jsonc"
        text=config.read_text(encoding="utf-8")
        self.assertIn("unified-free-capacity-retry",text)
        plugin=Path(__file__).resolve().parents[1]/".opencode/plugins/unified-free-capacity-retry/index.js"
        content=plugin.read_text(encoding="utf-8")
        self.assertIn("session.hook(\"retry\"", content)
        self.assertIn("event.decision", content)
        self.assertNotIn("anthropic/claude", content)

if __name__ == "__main__":
    unittest.main()
