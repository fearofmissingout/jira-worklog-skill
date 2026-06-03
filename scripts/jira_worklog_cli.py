#!/usr/bin/env python3
"""CLI helpers for the jira-worklog skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jira_tempo_client import (
    JiraTempoClient,
    field_preference,
    fetch_issue_details,
    select_allowed_option,
    summarize_tempo_worklogs,
)


CONFIRM_PHRASE = "SUBMIT_JIRA_WORKLOGS"


def emit(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
    issue_keys = [
        (worklog.get("issue") or {}).get("key")
        for worklog in worklogs
        if (worklog.get("issue") or {}).get("key")
    ]
    try:
        issue_details = fetch_issue_details(client, issue_keys)
    except Exception:
        issue_details = {}
    rows = summarize_tempo_worklogs(worklogs, issue_details=issue_details)
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


def cmd_resolve_issue_fields(args: argparse.Namespace) -> int:
    client = JiraTempoClient.from_env()
    try:
        client.login_session()
    except Exception:
        pass
    me = client.myself()
    rules = load_project_rules(args.local_rules)
    local_rule = rules.get(args.project_key, {})
    issue_type = args.issue_type or local_rule.get("issue_type") or "Task"
    intent_text = " ".join(value for value in [args.summary, args.description, args.intent] if value)
    fields_meta = issue_type_fields(client, args.project_key, issue_type)
    assignee = me.get("name") if local_rule.get("assignee") == "self" or args.assignee_self else None
    resolved = resolve_create_fields(fields_meta, local_rule, intent_text, assignee)
    create_fields = {
        "project": {"key": args.project_key},
        "summary": args.summary,
        "issuetype": {"name": issue_type},
        **resolved["extra_fields"],
    }
    if args.description:
        create_fields["description"] = args.description
    emit(
        {
            "project_key": args.project_key,
            "issue_type": issue_type,
            "create_fields": create_fields,
            "resolved_fields": resolved["resolved_fields"],
            "questions": resolved["questions"],
            "blocking_errors": resolved["blocking_errors"],
            "encoding": {
                "request_body": "UTF-8 JSON",
                "stdout": "UTF-8",
                "note": "If a browser page shows mojibake while Jira/Tempo API readback is correct, treat it as a display/cache issue before rewriting data.",
            },
        }
    )
    return 0


def load_plan(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_project_rules(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    rule_path = Path(path)
    if not rule_path.exists():
        return {}
    return json.loads(rule_path.read_text(encoding="utf-8"))


def issue_type_fields(client: JiraTempoClient, project_key: str, issue_type: str) -> dict[str, Any]:
    metadata = client.request(
        "GET",
        "/rest/api/2/issue/createmeta",
        query={
            "projectKeys": project_key,
            "issuetypeNames": issue_type,
            "expand": "projects.issuetypes.fields",
        },
    )
    projects = metadata.get("projects") or []
    if not projects:
        raise RuntimeError(f"No create metadata found for project {project_key}.")
    issue_types = projects[0].get("issuetypes") or []
    selected = next((item for item in issue_types if item.get("name") == issue_type), None)
    if not selected:
        raise RuntimeError(f"Issue type {issue_type} is not available for project {project_key}.")
    return selected.get("fields") or {}


def resolve_create_fields(
    fields_meta: dict[str, Any],
    local_rule: dict[str, Any],
    intent_text: str,
    assignee: str | None,
) -> dict[str, Any]:
    core_fields = {"project", "summary", "issuetype"}
    extra_fields: dict[str, Any] = {}
    resolved_fields = []
    questions = []
    blocking_errors = []
    option_hints = local_rule.get("field_option_hints") or {}

    if assignee and "assignee" in fields_meta:
        extra_fields["assignee"] = {"name": assignee}
        resolved_fields.append({"field": "assignee", "value": "self", "reason": "authenticated user"})

    if local_rule.get("priority_id") and "priority" in fields_meta:
        extra_fields["priority"] = {"id": str(local_rule["priority_id"])}
        resolved_fields.append({"field": "priority", "id": str(local_rule["priority_id"]), "reason": "local rule"})

    candidate_field_ids = {
        field_id
        for field_id, field_meta in fields_meta.items()
        if field_meta.get("required") and field_id not in core_fields
    }
    if local_rule.get("category_field"):
        candidate_field_ids.add(str(local_rule["category_field"]))

    for field_id in sorted(candidate_field_ids):
        field_meta = fields_meta.get(field_id)
        if not field_meta:
            blocking_errors.append(f"{field_id} is configured locally but is not available in Jira create metadata.")
            continue
        allowed_values = field_meta.get("allowedValues") or []
        preferred_value, preferred_id = field_preference(local_rule, field_id)
        if allowed_values:
            field_hints = option_hints.get(field_id) or {}
            if not isinstance(field_hints, dict):
                field_hints = {}
            selected = select_allowed_option(
                allowed_values,
                intent_text=intent_text,
                preferred_value=preferred_value,
                preferred_id=preferred_id,
                extra_hints={key: value for key, value in field_hints.items()},
            )
            if selected:
                extra_fields[field_id] = selected["payload"]
                resolved_fields.append(
                    {
                        "field": field_id,
                        "field_name": field_meta.get("name"),
                        "id": selected.get("id"),
                        "value": selected.get("value"),
                        "score": selected.get("score"),
                        "reasons": selected.get("reasons"),
                    }
                )
                continue
            questions.append(
                f"{field_meta.get('name') or field_id} needs one of {len(allowed_values)} options; no confident match from intent."
            )
            continue
        questions.append(f"{field_meta.get('name') or field_id} is required but has no selectable allowed values.")

    return {
        "extra_fields": extra_fields,
        "resolved_fields": resolved_fields,
        "questions": questions,
        "blocking_errors": blocking_errors,
    }


def validate_submittable(plan: dict[str, Any]) -> list[str]:
    errors = []
    if plan.get("blocking_errors"):
        errors.extend(plan["blocking_errors"])
    if plan.get("questions"):
        errors.extend(plan["questions"])
    for issue in plan.get("issue_drafts", []):
        if issue.get("needs_issue_creation") and not (
            issue.get("category")
            or issue.get("category_id")
            or issue.get("extra_fields")
        ):
            errors.append(f"{issue.get('issue_summary')} needs required issue fields before issue creation.")
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
                category_id=issue.get("category_id"),
                category_field=issue.get("category_field", "customfield_13900"),
                description=issue.get("description"),
                assignee=issue.get("assignee"),
                priority_id=issue.get("priority_id"),
                extra_fields=issue.get("extra_fields"),
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

    resolve = sub.add_parser("resolve-issue-fields", help="Resolve Jira required issue fields from metadata and intent")
    resolve.add_argument("--project-key", required=True)
    resolve.add_argument("--issue-type")
    resolve.add_argument("--summary", required=True)
    resolve.add_argument("--description")
    resolve.add_argument("--intent")
    resolve.add_argument("--local-rules", help="Path to .local/project-rules.local.json")
    resolve.add_argument("--assignee-self", action="store_true")
    resolve.set_defaults(func=cmd_resolve_issue_fields)

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
