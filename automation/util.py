import os
from pathlib import Path
from router.config import load_env, flag, integer

load_env()
ROOT = Path(__file__).resolve().parents[1]


def project():
    raw = os.getenv("PROJECT_PATH", "").strip()
    return Path(raw).expanduser().resolve() if raw else ROOT


def tasks_db():
    return ROOT / ".agent-runtime" / "tasks.sqlite3"


def project_files(path):
    folder = path / ".agent"
    folder.mkdir(parents=True, exist_ok=True)
    templates = ROOT / "project-template" / ".agent"
    if templates.is_dir():
        for src in templates.iterdir():
            target = folder / src.name
            if src.is_file() and not target.exists():
                target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    source = ROOT / "project-template" / "AGENTS.md"
    instructions = path / "AGENTS.md"
    if source.is_file() and not instructions.exists():
        (path / "AGENTS.md").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    # Propagate process-control rules to projects bootstrapped before this change.
    if instructions.is_file():
        current = instructions.read_text(encoding="utf-8")
        marker = "## Owner-controlled application processes"
        template_text = source.read_text(encoding="utf-8") if source.is_file() else ""
        if marker not in current and marker in template_text:
            instructions.write_text(
                current.rstrip() + "\n\n" + template_text[template_text.index(marker):].strip() + "\n",
                encoding="utf-8")
    return folder
