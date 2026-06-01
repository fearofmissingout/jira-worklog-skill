#!/usr/bin/env python3
"""Check for and apply updates for a git-installed jira-worklog skill."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def default_skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def run_git(skill_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(skill_dir), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_output(skill_dir: Path, *args: str, check: bool = True) -> str:
    result = run_git(skill_dir, *args, check=check)
    return result.stdout.strip()


def is_git_repo(skill_dir: Path) -> bool:
    if not skill_dir.exists():
        return False
    result = run_git(skill_dir, "rev-parse", "--is-inside-work-tree", check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def has_local_changes(skill_dir: Path) -> bool:
    status = git_output(skill_dir, "status", "--short")
    return bool(status.strip())


def upstream_ref(skill_dir: Path) -> str | None:
    result = run_git(skill_dir, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def check_updates(skill_dir: Path, fetch: bool = True) -> dict[str, Any]:
    skill_dir = skill_dir.resolve()
    if not is_git_repo(skill_dir):
        return {
            "status": "not_git",
            "skill_dir": str(skill_dir),
            "message": "Skill directory is not a Git checkout. Reinstall or migrate it as a git clone before automatic updates.",
        }

    if fetch:
        fetch_result = run_git(skill_dir, "fetch", "--quiet", check=False)
        if fetch_result.returncode != 0:
            return {
                "status": "fetch_failed",
                "skill_dir": str(skill_dir),
                "message": fetch_result.stderr.strip() or "git fetch failed",
            }

    upstream = upstream_ref(skill_dir)
    if not upstream:
        return {
            "status": "no_upstream",
            "skill_dir": str(skill_dir),
            "dirty": has_local_changes(skill_dir),
            "message": "Current branch has no upstream. Set an upstream before automatic updates.",
        }

    head = git_output(skill_dir, "rev-parse", "HEAD")
    remote = git_output(skill_dir, "rev-parse", upstream)
    base = git_output(skill_dir, "merge-base", "HEAD", upstream)
    dirty = has_local_changes(skill_dir)

    if head == remote:
        status = "up_to_date"
    elif head == base:
        status = "update_available"
    elif remote == base:
        status = "local_ahead"
    else:
        status = "diverged"

    return {
        "status": status,
        "skill_dir": str(skill_dir),
        "upstream": upstream,
        "head": head,
        "remote": remote,
        "dirty": dirty,
    }


def update_skill(skill_dir: Path) -> dict[str, Any]:
    state = check_updates(skill_dir, fetch=True)
    status = state["status"]

    if status == "up_to_date":
        state["message"] = "Already up to date."
        return state

    if status != "update_available":
        state.setdefault("message", f"Cannot update automatically while status is {status}.")
        return state

    if state.get("dirty"):
        state["status"] = "dirty"
        state["message"] = "Local Git changes exist. Commit, stash, move, or discard them before updating."
        return state

    pull = run_git(skill_dir.resolve(), "pull", "--ff-only", check=False)
    if pull.returncode != 0:
        state["status"] = "pull_failed"
        state["message"] = pull.stderr.strip() or "git pull --ff-only failed"
        return state

    updated = check_updates(skill_dir, fetch=False)
    updated["status"] = "updated"
    updated["message"] = pull.stdout.strip() or "Updated successfully."
    return updated


def print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    status = result.get("status", "unknown")
    print(f"status: {status}")
    if result.get("skill_dir"):
        print(f"skill_dir: {result['skill_dir']}")
    if result.get("upstream"):
        print(f"upstream: {result['upstream']}")
    if "dirty" in result:
        print(f"dirty: {result['dirty']}")
    if result.get("message"):
        print(result["message"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check or update a git-installed jira-worklog skill.")
    parser.add_argument("command", choices=["check", "update"], nargs="?", default="check")
    parser.add_argument("--dir", default=str(default_skill_dir()), help="Skill installation directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args(argv)

    skill_dir = Path(args.dir)
    result = check_updates(skill_dir) if args.command == "check" else update_skill(skill_dir)
    print_result(result, args.json)

    if result["status"] in {"up_to_date", "update_available", "updated"}:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
