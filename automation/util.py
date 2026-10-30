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
    # Add newly introduced rules to existing projects, without rewriting old
    # instructions or creating repeated duplicate sections.
    if instructions.is_file() and source.is_file():
        current = instructions.read_text(encoding="utf-8")
        template_text = source.read_text(encoding="utf-8")
        for marker in ("## Owner-controlled application processes",
                       "## Project-level review checkpoint"):
            if marker not in current and marker in template_text:
                remaining = template_text[template_text.index(marker):]
                next_heading = remaining.find("\n## ", 4)
                section = remaining if next_heading == -1 else remaining[:next_heading]
                current = current.rstrip() + "\n\n" + section.strip() + "\n"
        if current != instructions.read_text(encoding="utf-8"):
            instructions.write_text(current, encoding="utf-8")
    return folder
