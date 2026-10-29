"""Task supervisor: queue, check capacity, run one OpenCode job, checkpoint, verify.

The worker is intentionally single-agent. It cannot push or deploy automatically.
Owner reviews all finished tasks; no test pass is asserted without an exit code.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .mail import notify
from .records import Tasks
from .util import ROOT, flag, integer, project, project_files, tasks_db


def api_status():
    host = os.getenv("ROUTER_HOST", "127.0.0.1")
    port = os.getenv("ROUTER_PORT", "4030")
    request = urllib.request.Request(
        "http://" + host + ":" + port + "/router/status",
        headers={"Authorization": "Bearer " + os.getenv("FREE_ROUTER_KEY","local-agent-only")})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def git(path, *args):
    done = subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, timeout=30)
    return (done.stdout + done.stderr)[-4000:],done.returncode


def checkpoint(path, task, note, tests="Not run"):
    folder = project_files(path)
    status, _ = git(path, "status", "--short")
    diff, _ = git(path, "diff", "--stat")
    content = (
        "# Verified Agent Handoff\n\n"
        "Task ID: " + str(task["id"]) + "\n"
        "Goal: " + task["goal"] + "\n"
        "Checkpoint UTC: " + datetime.now(timezone.utc).isoformat() + "\n"
        "State: " + note + "\n\n"
        "## Current Git Status\n\n" + status + "\n"
        "## Working Tree Diff Summary\n\n" + diff + "\n"
        "## Local Test Evidence\n\n" + tests + "\n"
        "## Next action\n\n"
        "Inspect git diff, verify the implementation and resume acceptance criteria.\n"
    )
    (folder / "SUPERVISOR_STATE.md").write_text(content, encoding="utf-8")


def run_task(tasks, task):
    location = Path(task["project"])
    if not location.is_dir() or not (location / ".git").exists():
        tasks.transition(task["id"], "awaiting_owner", "PROJECT_PATH must be an existing local git repository.")
        return
    project_files(location)
    try:
        capacity = api_status()
    except (OSError, urllib.error.URLError, ValueError):
        tasks.transition(task["id"], "waiting_capacity", "Router not reachable",
                         time.time()+120)
        return
    if not capacity.get("any_available"):
        tasks.transition(task["id"], "waiting_capacity", "Every configured free model unavailable",
                         time.time()+max(120,integer("WORKER_POLL_SECONDS",60)))
        return

    max_attempts = integer("MAX_TASK_ATTEMPTS", 2)
    if task["attempts"] >= max_attempts:
        tasks.transition(task["id"], "awaiting_owner", "Max execution attempts reached.")
        notify("[Unified Agent] Task paused: "+task["title"],
               "Task "+str(task["id"])+" needs owner direction. No further automatic retries.")
        return
    tasks.transition(task["id"], "running", "OpenCode job started", increment=True)
    checkpoint(location, task, "Started / previous modifications may exist.")
    prompt = (
        "Work ONLY on the assigned task. Read AGENTS.md, .agent/HANDOFF.md and .agent/OWNER_DIRECTION.md if present. "
        "Task ID "+str(task["id"])+". Goal: "+task["goal"]+". "
        "Document changes and precise next steps in .agent/HANDOFF.md. "
        "Run local tests where permitted. Do not push, deploy, read .env or claim results you did not observe. "
        "If unsure, write .agent/OWNER_REQUEST.md describing the decision required and STOP. "
        "This may be a retry after an interrupted session: inspect existing changes before editing."
    )
    env = dict(os.environ)
    env["FREE_ROUTER_KEY"] = os.getenv("FREE_ROUTER_KEY", "local-agent-only")
    env["OPENCODE_CONFIG"] = str(ROOT / "opencode.jsonc")
    env["OPENCODE_CONFIG_DIR"] = str(ROOT / ".opencode")
    command = ["opencode","run","--standalone","--model","unified/auto-coder","--agent","build"]
    if flag("AUTONOMOUS_AUTO_APPROVE", False):
        command.append("--auto")
    command.append(prompt)
    timeout = max(60, integer("TASK_TIMEOUT_SECONDS",1800))
    try:
        result = subprocess.run(command, cwd=location, env=env, capture_output=True,
                                text=True, timeout=timeout)
        exit_code, text = result.returncode, (result.stdout+result.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        exit_code,text = 124,"OpenCode execution exceeded configured timeout."
    except OSError as error:
        exit_code,text = 127, "OpenCode failed to start: "+type(error).__name__
    logs = ROOT / ".agent-runtime"
    logs.mkdir(parents=True,exist_ok=True)
    (logs / ("task-"+str(task["id"])+".log")).write_text(text,encoding="utf-8")

    owner_request = location / ".agent" / "OWNER_REQUEST.md"
    if owner_request.is_file() and owner_request.read_text(encoding="utf-8").strip():
        question = owner_request.read_text(encoding="utf-8")[:3000]
        tasks.transition(task["id"],"awaiting_owner",question)
        checkpoint(location,task,"Owner direction required. Work paused.")
        notify("[Unified Agent] Approval needed — "+task["title"],
               "Task #"+str(task["id"])+" requests a decision:\n\n"+question+
               "\n\nUse the local agent CLI decide command to provide directions. Replies by email are not parsed.")
        return

    test_result = "Not run; set TEST_COMMAND in .env for acceptance."
    tests_passed = False
    test_command = os.getenv("TEST_COMMAND", "").strip()
    if exit_code == 0 and test_command:
        try:
            # Explicit operator-supplied command only; not generated by a cloud model.
            verified = subprocess.run(test_command, shell=True, cwd=location, capture_output=True,
                                      text=True, timeout=600)
            tests_passed = verified.returncode == 0
            test_result = "Configured test command: "+test_command+"\nExit: "+str(verified.returncode)+"\n"+(
                verified.stdout+verified.stderr)[-3000:]
        except (subprocess.TimeoutExpired, OSError) as error:
            test_result = "Test runner error: "+type(error).__name__
    checkpoint(location, task, "OpenCode exit="+str(exit_code), test_result)
    if exit_code == 0 and tests_passed:
        tasks.transition(task["id"], "ready_for_review", "Test exit 0; owner review required.")
        notify("[Unified Agent] Ready for review — "+task["title"],
               "Task #"+str(task["id"])+" passed the configured test command. "
               "Please inspect the local diff before approval; no changes were pushed.")
    elif exit_code in (124, 127):
        tasks.transition(task["id"],"waiting_capacity","Execution interruption; inspect checkpoint",
                         time.time()+300)
    elif task["attempts"]+1 >= max_attempts:
        tasks.transition(task["id"],"awaiting_owner","Tests failed or agent execution failed; review logs")
        notify("[Unified Agent] Task blocked — "+task["title"],
               "Task #"+str(task["id"])+" exhausted retry attempts. Inspect .agent/HANDOFF.md and task log.")
    else:
        tasks.transition(task["id"],"waiting_capacity",
                         "Unverified / failed execution, scheduled bounded retry",time.time()+300)


def worker_once(tasks):
    if not flag("AUTONOMOUS_ENABLED",False):
        print("AUTONOMOUS_ENABLED=false. No unattended coding will run.")
        return
    if not flag("AUTONOMOUS_AUTO_APPROVE",False):
        print("AUTONOMOUS_AUTO_APPROVE=false: unattended tool approvals may block. Enable only in a sandbox.")
        return
    task = tasks.next(max(1,integer("MAX_TASKS_PER_DAY",3)),
                      max(600,integer("TASK_TIMEOUT_SECONDS",1800))+300)
    if task:
        print("Executing task",task["id"],task["title"])
        run_task(tasks,task)
    else:
        print("No eligible queued tasks.")


def main():
    p = argparse.ArgumentParser(description="Unified coding agent supervisor")
    subs = p.add_subparsers(dest="cmd",required=True)
    a = subs.add_parser("add")
    a.add_argument("goal")
    a.add_argument("--title",default="Coding task")
    d = subs.add_parser("decide")
    d.add_argument("id",type=int)
    d.add_argument("direction")
    subs.add_parser("init-project")
    subs.add_parser("status")
    subs.add_parser("doctor")
    subs.add_parser("once")
    subs.add_parser("worker")
    args = p.parse_args()
    tasks = Tasks(tasks_db())
    if args.cmd == "init-project":
        target = project()
        if not (target / ".git").is_dir():
            raise SystemExit("PROJECT_PATH must refer to an existing local Git repository")
        print("Initialized",project_files(target))
        initial = os.getenv("INITIAL_TASK","").strip()
        if initial:
            tid = tasks.add("Initial task",initial,str(target),dedupe=True)
            print("Initial task ready:",tid)
    elif args.cmd == "add":
        if not (project() / ".git").is_dir():
            raise SystemExit("PROJECT_PATH must be a local Git repository")
        print("New task #",tasks.add(args.title,args.goal,str(project())))
    elif args.cmd == "decide":
        task = tasks.get(args.id)
        if not task or task["status"] not in ("awaiting_owner","ready_for_review"):
            print("Task not eligible or ID not found")
        else:
            if task["status"] == "awaiting_owner":
                folder = project_files(Path(task["project"]))
                (folder / "OWNER_DIRECTION.md").write_text(
                    "Task #"+str(args.id)+" owner direction:\n"+args.direction+"\n",encoding="utf-8")
                (folder / "OWNER_REQUEST.md").write_text("",encoding="utf-8")
            print("Decision saved" if tasks.approve(args.id,args.direction) else
                  "Could not save decision")
    elif args.cmd == "status":
        print(json.dumps(tasks.all(),indent=2))
        try:
            print(json.dumps(api_status(),indent=2))
        except (OSError,ValueError):
            print("Router is offline or unauthenticated.")
    elif args.cmd == "doctor":
        print("Project:",project())
        print("Git repo:",(project() / ".git").is_dir())
        print("Configured:", [(k,bool(os.getenv(k))) for k in
                             ("KILO_API_KEY","GEMINI_API_KEY","OPENROUTER_API_KEY")])
        print("Autonomous:",flag("AUTONOMOUS_ENABLED",False))
        print("Auto approvals:",flag("AUTONOMOUS_AUTO_APPROVE",False))
        try:
            s=api_status()
            print("Router reachable:",s["mode"],"eligible:",s["any_available"])
        except (OSError,ValueError):
            print("Router not running yet.")
    elif args.cmd == "once":
        worker_once(tasks)
    elif args.cmd == "worker":
        while True:
            worker_once(tasks)
            time.sleep(max(30,integer("WORKER_POLL_SECONDS",60)))


if __name__ == "__main__":
    main()
