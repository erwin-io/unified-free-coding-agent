"""Read approved tasks from each project's own backlog, without implicit approval."""
import re
from pathlib import Path

HEADING = re.compile(r"^##\s+(TASK-[A-Za-z0-9-]+)\s*:\s*(.+?)\s*$", re.I | re.M)
STATUS = re.compile(r"^\s*Status\s*:\s*(.*?)\s*$", re.I | re.M)


def approved_items(path: Path):
    backlog = path / ".agent" / "BACKLOG.md"
    if not backlog.is_file():
        return []
    contents = backlog.read_text(encoding="utf-8")
    matches = list(HEADING.finditer(contents))
    items = []
    seen = set()
    for i, match in enumerate(matches):
        task_id = match.group(1).upper()
        if task_id in seen:
            raise ValueError("Duplicate backlog task ID: " + task_id)
        seen.add(task_id)
        section = contents[match.end():matches[i+1].start() if i+1<len(matches) else len(contents)]
        status = STATUS.search(section)
        if not status or status.group(1).strip().lower() != "approved":
            continue
        title = match.group(2).strip()
        if title:
            items.append((task_id, title, (title+"\n\n"+section.strip())[:16000]))
    return items


def sync_approved_tasks(path: Path, tasks):
    imported = 0
    for task_id, title, goal in approved_items(path):
        existing = tasks.db.execute(
            "SELECT id FROM tasks WHERE project=? AND source_id=?",
            (str(path), task_id)).fetchone()
        if existing:
            continue
        tasks.add(title, goal, str(path), source_id=task_id)
        imported += 1
    return imported
