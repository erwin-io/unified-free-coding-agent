"""Language scaffolding: preserve data and build real supported host templates."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.scaffold import ScaffoldError, scaffold


class ScaffoldTests(unittest.TestCase):
    def test_node_project_generates_real_files_and_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "web-lab"
            result = scaffold(dest, "node-web", verify=True, git=False)
            self.assertTrue(result["verified"])
            self.assertTrue((dest / "server.js").is_file())
            self.assertTrue((dest / ".agent" / "BACKLOG.md").is_file())
            self.assertTrue((dest / "public" / "app.js").is_file())

    def test_existing_extra_file_is_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "web-lab"
            dest.mkdir()
            (dest / "filestructure.txt").write_text("keep user file",encoding="utf-8")
            scaffold(dest, "node-web", verify=False, git=False)
            self.assertEqual((dest / "filestructure.txt").read_text(), "keep user file")

    def test_conflict_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "web-lab"
            dest.mkdir()
            (dest / "server.js").write_text("user edits",encoding="utf-8")
            with self.assertRaises(ScaffoldError):
                scaffold(dest, "node-web", verify=False, git=False)
            self.assertEqual((dest / "server.js").read_text(), "user edits")
            self.assertFalse((dest / "package.json").exists())

    def test_micropython_starter_host_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "pico-firmware"
            result = scaffold(dest, "micropython", verify=True, git=False)
            self.assertTrue(result["verified"])
            self.assertIn("micropython",result["stack"])
            self.assertTrue((dest / "tools" / "device.ps1").is_file())
            self.assertTrue((dest / ".agent" / "validation.json").is_file())

    @unittest.skipUnless(shutil.which("cmake") and shutil.which("ctest"), "Requires CMake")
    def test_cpp_host_build_and_ctest(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "cpp-lab"
            result = scaffold(dest, "cpp", verify=True, git=False)
            self.assertTrue(result["verified"])
            self.assertTrue((dest / "build").is_dir())

    def test_angular_generation_is_cli_driven(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "angular-lab"
            def cli_stub(argv, directory, timeout=600):
                if argv[0] == "npx":
                    app = directory / "frontend" / "src" / "app"
                    app.mkdir(parents=True)
                    (app / "app.ts").write_text("GENERATED_BY_CLI",encoding="utf-8")
            with patch("automation.scaffold._command",side_effect=cli_stub):
                result = scaffold(dest, "angular-node", verify=False, git=False)
            self.assertFalse(result["verified"])
            self.assertIn("readonly status", (dest/"frontend/src/app/app.ts").read_text())
            self.assertTrue((dest/"backend/server.mjs").is_file())
            self.assertTrue((dest/"frontend/proxy.conf.json").is_file())

    def test_existing_git_project_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "existing"
            (dest/".git").mkdir(parents=True)
            (dest/"app.txt").write_text("original")
            result = scaffold(dest, "cpp", verify=False, git=False)
            self.assertTrue(result["existing_git"])
            self.assertFalse((dest/"CMakeLists.txt").exists())


if __name__ == "__main__":
    unittest.main()
