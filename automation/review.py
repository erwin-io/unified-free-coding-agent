"""Project-level review packet: observed Git state and actual test evidence."""
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def git(project, *args):
    completed = subprocess.run(["git", *args], cwd=project, capture_output=True,
                               text=True, errors="replace", timeout=30)
    if completed.returncode:
        raise RuntimeError("Git inspection failed (" + " ".join(args) + "): " + completed.stderr[-400:])
    return completed.stdout.strip()

def section(path, limit=6000):
    if not path.is_file():
        return "Not provided."
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] + ("\n[truncated]" if len(text) > limit else "")

def feature_branch(task):
    raw = task.get("source_id") or "TASK-" + str(task["id"])
    slug = re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-")
    return "agent/" + slug

def ensure_task_branch(project, task):
    """Never execute unattended development directly on main/master."""
    current = git(project, "branch", "--show-current")
    desired = feature_branch(task)
    if current == desired:
        return desired
    if current not in ("main", "master"):
        raise RuntimeError("Expected " + desired + " or main/master, found " + current)
    if git(project, "branch", "--list", desired):
        raise RuntimeError("Existing task branch requires owner checkout: " + desired)
    git(project, "switch", "-c", desired)
    return desired

def write_review_packet(project, task=None):
    project = Path(project).resolve()
    if not (project / ".git").exists():
        raise ValueError("Review project is not a local Git repository")
    folder = project / ".agent"
    folder.mkdir(exist_ok=True)
    branch = git(project, "branch", "--show-current")
    sha = git(project, "rev-parse", "HEAD")
    status = git(project, "status", "--short", "--untracked-files=normal")
    stat = git(project, "diff", "--stat", "HEAD")
    name_status = git(project, "diff", "--name-status", "HEAD")
    task_name = (str(task["id"]) + " - " + task["title"]) if task else "Interactive session"
    parts = [
        "# TECH LEAD REVIEW PACKET - NOT APPROVED",
        "Created UTC: " + datetime.now(timezone.utc).isoformat(),
        "Project: " + str(project),
        "Task: " + task_name,
        "Branch: " + (branch or "(detached)"),
        "HEAD SHA: " + sha,
        "Merge / deployment: NOT AUTHORIZED",
        "",
        "## Project checklist", section(folder / "CHECKLIST.md"),
        "## Backlog / acceptance criteria", section(folder / "BACKLOG.md"),
        "## Changed/untracked files", "~~~",
        status or "(clean)", "~~~",
        "## Tracked changes summary", "~~~",
        stat or "(no tracked changes)", "~~~",
        "## Changed tracked files", "~~~",
        name_status or "(none)", "~~~",
        "## Independent test evidence", section(folder / "TEST_EVIDENCE.md"),
        "## Agent handoff", section(folder / "HANDOFF.md"),
        "## Tech Lead review questions",
        "- Were new feature-specific tests added and actually executed?",
        "- Do changed API/UI contracts and security constraints pass inspection?",
        "- Is the actual source diff needed before an approval decision?",
        "- Are tests, branch, and review scope consistent?",
        "",
        "Decision: PENDING (APPROVED / CHANGES REQUIRED / BLOCKED)",
        "Reviewer notes: Must be filled in by the Tech Lead.",
        "Do not treat this packet or successful old tests as approval.",
        "A GitHub PR and merge require separate owner authorization.",
        "",
    ]
    target = folder / "TECH_LEAD_REVIEW.md"
    target.write_text("\n".join(parts), encoding="utf-8")
    return target
