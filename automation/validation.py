"""Repository-owned test discovery and evidence; never consume a TEST_COMMAND env."""
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Validation:
    passed: bool
    commands: tuple
    summary: str


def _custom(path):
    config = path / ".agent" / "validation.json"
    if not config.is_file():
        return None
    obj = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("validation.json must be a JSON object")
    commands = obj.get("commands")
    if not isinstance(commands, list) or not (1 <= len(commands) <= 8):
        raise ValueError(".agent/validation.json requires 1–8 commands")
    for argv in commands:
        if (not isinstance(argv, list) or not (1 <= len(argv) <= 16) or
                any(not isinstance(a, str) or not a or "\x00" in a for a in argv)):
            raise ValueError("Validation commands must be argument string arrays")
    return [tuple(args) for args in commands]


def discover(path):
    """Use existing trusted test scripts; no LLM-supplied shell command."""
    custom = _custom(path)
    if custom is not None:
        return custom
    manifest = path / "package.json"
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        checks = []
        if isinstance(scripts, dict):
            npm = "npm.cmd" if os.name == "nt" else "npm"
            for key in ("test", "typecheck", "lint"):
                script = scripts.get(key)
                if isinstance(script, str) and script.strip():
                    if "no test specified" in script.lower() or script.strip() == "exit 1":
                        continue
                    checks.append((npm, "run", key))
        if checks:
            return checks
    if (path / "platformio.ini").exists():
        # Build embedded firmware, never upload or erase it automatically.
        return [("pio", "run")]
    if (path / "CMakeLists.txt").exists():
        return [("cmake", "-S", ".", "-B", "build"),
                ("cmake", "--build", "build", "--config", "Debug"),
                ("ctest", "--test-dir", "build", "-C", "Debug", "--output-on-failure")]
    if (path / "go.mod").exists():
        return [("go", "test", "./...")]
    if (path / "Cargo.toml").exists():
        return [("cargo", "test")]
    if (path / "pom.xml").exists():
        wrapper = path / ("mvnw.cmd" if os.name == "nt" else "mvnw")
        return [(str(wrapper), "test")] if wrapper.exists() else [("mvn", "test")]
    gradle = path / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if gradle.is_file():
        return [(str(gradle), "test")]
    if list(path.glob("*.sln")) or list(path.glob("*.slnx")) or list(path.glob("*.csproj")):
        return [("dotnet", "test")]
    pyproject = path / "pyproject.toml"
    if ((path / "pytest.ini").exists() or (path / "tests").is_dir() or
            (pyproject.is_file() and "pytest" in pyproject.read_text(encoding="utf-8").lower())):
        project_py = path / ".venv" / ("Scripts/python.exe" if os.name=="nt" else "bin/python")
        return [(str(project_py) if project_py.is_file() else "python", "-m", "pytest", "-q")]
    return []


def validate_project(path):
    folder = path / ".agent"
    folder.mkdir(parents=True, exist_ok=True)
    evidence = folder / "TEST_EVIDENCE.md"
    try:
        commands = discover(path)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        summary = "Validation configuration error: "+str(error)
        evidence.write_text("# Independent Validation\n\n"+summary+"\n", encoding="utf-8")
        return Validation(False, (), summary)
    if not commands:
        summary = ("No runnable tests discovered. Add actual project tests or "
                   ".agent/validation.json with commands; owner review required.")
        evidence.write_text("# Independent Validation\n\n"+summary+"\n", encoding="utf-8")
        return Validation(False, (), summary)
    lines = ["# Independent Validation", "","UTC: "+datetime.now(timezone.utc).isoformat(), ""]
    passed = True
    for command in commands:
        lines.extend(["## Command", "Arguments: "+repr(list(command))])
        try:
            process = subprocess.run(command, cwd=path, capture_output=True, text=True,
                                     errors="replace", timeout=600, env={**os.environ, "CI":"true"})
            exit_code = process.returncode
            output = (process.stdout+"\n"+process.stderr)[-5000:]
        except subprocess.TimeoutExpired:
            exit_code, output = 124, "Validation timed out after 600 seconds."
        except OSError as error:
            exit_code, output = 127, "Unable to launch validation: "+type(error).__name__
        lines.extend(["Exit code: "+str(exit_code),"Output:",output,""])
        if exit_code != 0:
            passed = False
            break
    summary = "Independent project validation passed" if passed else "Independent project validation failed"
    lines.insert(2, "Result: "+summary)
    evidence.write_text("\n".join(lines)+"\n", encoding="utf-8")
    return Validation(passed, tuple(commands), summary+"\n"+"\n".join(lines[-18:]))
