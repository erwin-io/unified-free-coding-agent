"""Safe stack-specific project bootstrap; projects own tasks, tools and tests.

Supports Node.js/vanilla web, Angular+Node.js, MicroPython and C++/CMake.
Never deletes or overwrites existing project files. Existing Git worktrees are
adopted without scaffolding. Firmware upload always requires separate approval.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .util import ROOT, project_files

STACKS = ("node-web", "angular-node", "micropython", "cpp")


class ScaffoldError(RuntimeError):
    pass


def _hash(path: Path):
    return hashlib.sha256(path.read_bytes()).digest()


def _command(argv, directory: Path, timeout=600):
    args = list(argv)
    if os.name == "nt" and args[0] in ("npm", "npx", "pnpm", "yarn"):
        args[0] += ".cmd"
    try:
        subprocess.run(args, cwd=directory, check=True, timeout=timeout)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ScaffoldError("Command failed: " + " ".join(str(v) for v in argv) +
                            ". Verify the toolchain, logs and generated files. " +
                            str(error)) from error


def _tool(name):
    if not shutil.which(name):
        raise ScaffoldError("Missing required development tool: " + name)


def _source(stack):
    return ROOT / ("examples/test-nodejs-web-app" if stack == "node-web"
                   else "templates/" + stack)


def _listed_files(source):
    return {str(p.relative_to(source)).replace("\\", "/"): p
            for p in source.rglob("*") if p.is_file()}


def _check_target(path):
    path = path.expanduser().resolve()
    if path.name in ("", ".", "..") or path == Path(path.anchor):
        raise ScaffoldError("Refusing to initialize a filesystem root")
    if path.exists() and (path.is_symlink() or not path.is_dir()):
        raise ScaffoldError("Project path must be a normal directory")
    # No symlink/junction traversal in project-owned paths.
    if path.exists():
        for item in path.rglob("*"):
            if item.is_symlink():
                raise ScaffoldError("Symlink present, cannot safely scaffold: " + str(item))
    return path


def _copy_checked(source, destination, allow_generated_angular=False):
    listed = _listed_files(source)
    # Scan ALL potential conflicts before writing a single template file.
    for name, origin in listed.items():
        target = destination / name
        if target.exists():
            if target.is_dir():
                raise ScaffoldError("Expected file but found directory: " + str(target))
            if _hash(origin) != _hash(target):
                if allow_generated_angular and name.startswith("frontend/src/app/"):
                    continue
                raise ScaffoldError("Existing file differs, refusing overwrite: " + str(target))
    copied = []
    for name, origin in listed.items():
        target = destination / name
        if target.exists() and not (allow_generated_angular and
                                    name.startswith("frontend/src/app/")):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
        copied.append(name)
    return copied


def _run_validation(stack, target):
    if stack == "node-web":
        _command(["node", "--test"], target)
        _command(["node", "--check", "server.js"], target)
        _command(["node", "--check", "public/app.js"], target)
    elif stack == "angular-node":
        _command(["npm", "install", "--prefix", "frontend", "--no-audit", "--no-fund"], target, 900)
        _command(["npm", "run", "test"], target)
        _command(["npm", "run", "lint"], target)
        _command(["npm", "run", "typecheck"], target, 900)
    elif stack == "micropython":
        _command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], target)
        _command([sys.executable, "-m", "compileall", "-q", "src"], target)
    elif stack == "cpp":
        _command(["cmake", "-S", ".", "-B", "build"], target)
        _command(["cmake", "--build", "build", "--config", "Debug"], target)
        _command(["ctest", "--test-dir", "build", "-C", "Debug", "--output-on-failure"], target)


def _init_git(target, paths):
    _command(["git", "init", "-b", "main"], target)
    # Explicitly stage the known scaffold and project-instruction files only.
    for path in sorted(paths):
        _command(["git", "add", "--", path], target)
    _command(["git", "-c", "user.name=Unified Agent Scaffold",
              "-c", "user.email=scaffold@local.invalid",
              "commit", "-m", "chore: initialize verified " + target.name + " scaffold"], target)


def scaffold(target: Path, stack: str, *, verify=True, git=True):
    if stack not in STACKS:
        raise ScaffoldError("Unknown project stack: " + stack)
    target = _check_target(Path(target))
    if (target / ".git").exists():
        return {"stack": stack, "path": str(target), "existing_git": True,
                "message": "Existing repository retained; no scaffold files were changed."}
    _tool("git")
    if stack in ("node-web", "angular-node"):
        _tool("node")
        _tool("npm")
        try:
            major = int(subprocess.check_output(
                ["node", "-p", "process.versions.node.split('.')[0]"],
                text=True, timeout=10).strip())
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            raise ScaffoldError("Cannot determine Node.js version") from error
        if major < 20:
            raise ScaffoldError("Node.js 20+ is required")
    if stack == "angular-node":
        _tool("npx")
    if stack == "cpp":
        _tool("cmake")
        _tool("ctest")
    source = _source(stack)
    if not source.exists():
        raise ScaffoldError("Missing scaffold template: " + str(source))

    # Angular CLI creates frontend. Do not reuse a partially created/unrelated
    # frontend without inspection; CLI output may have been interrupted.
    if stack == "angular-node":
        front = target / "frontend"
        if front.exists() and any(front.iterdir()):
            raise ScaffoldError("Existing frontend/ without Git; refusing Angular CLI overwrite. "
                                "Inspect the partial workspace first.")

    # For normal templates, preflight conflicts before any mutation.
    if stack != "angular-node":
        listed = _listed_files(source)
        for name, origin in listed.items():
            dest = target / name
            if dest.exists() and (dest.is_dir() or _hash(dest) != _hash(origin)):
                raise ScaffoldError("Conflicting existing file: " + str(dest))
    target.mkdir(parents=True, exist_ok=True)

    if stack == "angular-node":
        # Angular CLI is a scaffold tool; it is not an AI-inference provider.
        _command(["npx", "--yes", "--package", "@angular/cli", "ng", "new", "frontend",
                  "--directory", "frontend", "--routing", "--style", "css",
                  "--standalone", "--strict", "--skip-git", "--skip-install",
                  "--skip-tests", "--defaults", "--interactive=false"], target, 900)
        created = _copy_checked(source, target, allow_generated_angular=True)
        # Include all CLI-generated workspace files. frontend was empty before.
        known_paths = {"frontend", *created}
    else:
        created = _copy_checked(source, target)
        known_paths = set(_listed_files(source))

    # Shared agent notes and approvals remain in each target project.
    notes_dir = target / ".agent"
    before_notes = {str(p.relative_to(target)).replace(chr(92), "/")
                    for p in notes_dir.rglob("*") if p.is_file()} if notes_dir.is_dir() else set()
    had_agents = (target / "AGENTS.md").exists()
    folder = project_files(target)
    if not had_agents:
        known_paths.add("AGENTS.md")
    known_paths.update(str(p.relative_to(target)).replace(chr(92), "/")
                       for p in folder.rglob("*") if p.is_file() and
                       str(p.relative_to(target)).replace(chr(92), "/") not in before_notes)
    if verify:
        _run_validation(stack, target)
    if git:
        _init_git(target, known_paths)
    return {"stack": stack, "path": str(target), "existing_git": False,
            "files": len(known_paths), "verified": verify, "initialized_git": git}


def main():
    parser = argparse.ArgumentParser(description="Scaffold a supported coding stack")
    parser.add_argument("--stack", required=True, choices=STACKS)
    parser.add_argument("--target", required=True)
    parser.add_argument("--no-verify", action="store_true",
                        help="For development/debugging only; never marks checks as passed")
    args = parser.parse_args()
    try:
        result = scaffold(Path(args.target), args.stack, verify=not args.no_verify)
        print("Project result:", result)
    except ScaffoldError as error:
        parser.exit(1, "Scaffold halted safely: " + str(error) + "\n")


if __name__ == "__main__":
    main()
