#!/usr/bin/env python3
"""CLI helpers for the jira-worklog skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jira_tempo_client import JiraTempoClient, summarize_tempo_worklogs


CONFIRM_PHRASE = "SUBMIT_JIRA_WORKLOGS"


def emit(value: Any) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def cmd_me(_: argparse.Namespace) -> int:
    client = JiraTempoClient.from_env()
    try:
        client.login_session()
    except Exception:
        pass
    me = client.myself()
    emit(
        {
            "name": me.get("name"),
            "displayName": me.get("displayName"),
            "emailAddress": me.get("emailAddress"),
            "active": me.get("active"),
        }
    )
    return 0


def cmd_check_tempo(args: argparse.Namespace) -> int:
    client = JiraTempoClient.from_env()
    try:
        client.login_session()
    except Exception:
        pass
    worklogs = client.tempo_worklogs(args.date_from, args.date_to, args.username)
    rows = summarize_tempo_worklogs(worklogs)
    day_totals: dict[str, float] = {}
    for row in rows:
        day_totals[row["date"]] = round(day_totals.get(row["date"], 0.0) + float(row["hours"]), 2)
    emit(
        {
            "date_from": args.date_from,
            "date_to": args.date_to,
            "username": args.username,
            "worklog_count": len(worklogs),
            "rows": rows,
            "day_totals": [{"date": day, "hours": hours} for day, hours in sorted(day_totals.items())],
        }
    )
    return 0


def load_plan(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_submittable(plan: dict[str, Any]) -> list[str]:
    errors = []
    if plan.get("blocking_errors"):
        errors.extend(plan["blocking_errors"])
    if plan.get("questions"):
        errors.extend(plan["questions"])
    for issue in plan.get("issue_drafts", []):
        if issue.get("needs_issue_creation") and not issue.get("category"):
            errors.append(f"{issue.get('issue_summary')} needs category before issue creation.")
        if not issue.get("needs_issue_creation") and not issue.get("issue_key"):
            errors.append(f"{issue.get('issue_summary')} has no issue key.")
    return errors


def cmd_submit_plan(args: argparse.Namespace) -> int:
    if args.confirm != CONFIRM_PHRASE:
        emit(
            {
                "submitted": False,
                "error": f"Refusing to submit. Pass --confirm {CONFIRM_PHRASE} after user approval.",
            }
        )
        return 2

    plan = load_plan(args.plan)
    errors = validate_submittable(plan)
    if errors:
        emit({"submitted": False, "errors": errors})
        return 2

    client = JiraTempoClient.from_env()
    try:
        client.login_session()
    except Exception:
        pass

    created_issues = []
    created_worklogs = []
    for issue in plan.get("issue_drafts", []):
        issue_key = issue.get("issue_key")
        if issue.get("needs_issue_creation"):
            created = client.create_issue(
                project_key=issue["project_key"],
                summary=issue["issue_summary"],
                issue_type=issue.get("issue_type", "Task"),
                category=issue.get("category"),
                description=issue.get("description"),
            )
            issue_key = created["key"]
            created_issues.append({"key": issue_key, "summary": issue["issue_summary"]})

        for worklog in issue.get("worklogs", []):
            created = client.add_worklog(
                issue_key=issue_key,
                date=worklog["date"],
                hours=float(worklog["hours"]),
                comment=worklog.get("comment") or worklog.get("description") or issue["issue_summary"],
            )
            created_worklogs.append(
                {
                    "issue_key": issue_key,
                    "worklog_id": created.get("id"),
                    "date": worklog["date"],
                    "hours": float(worklog["hours"]),
                }
            )

    emit(
        {
            "submitted": True,
            "created_issues": created_issues,
            "created_worklogs": created_worklogs,
            "verify_next": "Run check-tempo for the submitted date range and compare day totals plus issue week boundaries.",
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jira worklog helpers for the jira-worklog skill")
    sub = parser.add_subparsers(dest="command", required=True)

    me = sub.add_parser("me", help="Check authenticated Jira user")
    me.set_defaults(func=cmd_me)

    check = sub.add_parser("check-tempo", help="Read Tempo worklogs for a date range")
    check.add_argument("--from", dest="date_from", required=True)
    check.add_argument("--to", dest="date_to", required=True)
    check.add_argument("--username", required=True)
    check.set_defaults(func=cmd_check_tempo)

    submit = sub.add_parser("submit-plan", help="Create missing issues and write worklogs from a plan JSON")
    submit.add_argument("--plan", required=True)
    submit.add_argument("--confirm", required=True)
    submit.set_defaults(func=cmd_submit_plan)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
