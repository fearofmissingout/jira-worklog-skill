#!/usr/bin/env python3
"""Create deterministic Jira worklog drafts from structured intent JSON.

The assistant should parse natural language into this structured input first,
then call this script to enforce repeatable worklog planning rules.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import defaultdict
from typing import Any


DAILY_LIMIT_HOURS = 8.0


def load_default_categories() -> dict[str, str]:
    raw = os.environ.get("JIRA_DEFAULT_CATEGORIES_JSON")
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("JIRA_DEFAULT_CATEGORIES_JSON must be a JSON object")
    return {str(key): str(value) for key, value in parsed.items()}


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def iso_week_start(day: dt.date) -> dt.date:
    return day - dt.timedelta(days=day.weekday())


def iso_week_label(day: dt.date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += dt.timedelta(days=1)
    return days


def is_workday(day: dt.date, non_workdays: set[dt.date], extra_workdays: set[dt.date]) -> bool:
    if day in non_workdays:
        return False
    if day in extra_workdays:
        return True
    return day.weekday() < 5


def clean_summary(text: str) -> str:
    return " ".join(str(text).strip().split())


def match_existing_issue(
    week_start: dt.date,
    description: str,
    existing_issues: list[dict[str, Any]],
) -> str | None:
    needle = clean_summary(description).lower()
    for issue in existing_issues:
        if issue.get("week_start") != week_start.isoformat():
            continue
        summary = clean_summary(issue.get("summary", "")).lower()
        if needle and needle in summary:
            return issue.get("key")
        if not needle and issue.get("key"):
            return issue.get("key")
    return None


def default_weekly_activities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    start = parse_date(payload["date_from"])
    end = parse_date(payload["date_to"])
    non_workdays = {parse_date(value) for value in payload.get("non_workdays", [])}
    extra_workdays = {parse_date(value) for value in payload.get("extra_workdays", [])}
    hours = float(payload.get("default_hours", DAILY_LIMIT_HOURS))
    description = payload.get("description") or "Worklog"

    activities = []
    for day in daterange(start, end):
        if is_workday(day, non_workdays, extra_workdays):
            activities.append(
                {
                    "date": day.isoformat(),
                    "description": description,
                    "hours": hours,
                }
            )
    return activities


def group_issue_drafts(payload: dict[str, Any], activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    project = payload["project"]
    category = payload.get("category") or load_default_categories().get(project["key"])
    existing_issues = payload.get("existing_issues", [])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for activity in activities:
        day = parse_date(activity["date"])
        week_start = iso_week_start(day)
        description = clean_summary(activity["description"])

        explicit_daily = bool(payload.get("activities"))
        grouping_description = description if explicit_daily else clean_summary(payload.get("description") or description)
        group_key = (week_start.isoformat(), grouping_description)
        grouped[group_key].append(
            {
                "date": day.isoformat(),
                "hours": float(activity["hours"]),
                "description": description,
                "comment": activity.get("comment") or f"Working on: {description}",
            }
        )

    drafts = []
    for (week_start_text, description), worklogs in sorted(grouped.items()):
        week_start = parse_date(week_start_text)
        issue_key = match_existing_issue(week_start, description, existing_issues)
        summary = f"{iso_week_label(week_start)} {description}"
        drafts.append(
            {
                "project_key": project["key"],
                "project_name": project.get("name"),
                "week_start": week_start.isoformat(),
                "week_end": (week_start + dt.timedelta(days=6)).isoformat(),
                "issue_key": issue_key,
                "needs_issue_creation": issue_key is None,
                "issue_summary": summary,
                "issue_type": payload.get("issue_type", "Task"),
                "category": category,
                "worklogs": sorted(worklogs, key=lambda item: item["date"]),
            }
        )
    return drafts


def validate_plan(issue_drafts: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    questions: list[str] = []
    blocking_errors: list[str] = []
    totals: dict[str, float] = defaultdict(float)

    for issue in issue_drafts:
        week_start = parse_date(issue["week_start"])
        week_end = parse_date(issue["week_end"])
        if issue["needs_issue_creation"] and issue.get("category") is None:
            questions.append(
                f"{issue['project_key']} needs category/custom required fields before creating {issue['issue_summary']}."
            )
        for worklog in issue["worklogs"]:
            day = parse_date(worklog["date"])
            if not (week_start <= day <= week_end):
                blocking_errors.append(
                    f"{issue['issue_summary']} has {day.isoformat()}, outside {issue['week_start']} to {issue['week_end']}."
                )
            totals[day.isoformat()] += float(worklog["hours"])

    for day, hours in sorted(totals.items()):
        rounded = round(hours, 2)
        if rounded > DAILY_LIMIT_HOURS:
            blocking_errors.append(
                f"{day} totals {rounded}h, above the {DAILY_LIMIT_HOURS}h daily limit."
            )

    return questions, blocking_errors


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    if "project" not in payload or "key" not in payload["project"]:
        raise ValueError("payload.project.key is required")
    activities = payload.get("activities") or default_weekly_activities(payload)
    issue_drafts = group_issue_drafts(payload, activities)
    questions, blocking_errors = validate_plan(issue_drafts)
    return {
        "issue_drafts": issue_drafts,
        "questions": questions,
        "blocking_errors": blocking_errors,
    }


def main() -> int:
    payload = json.load(sys.stdin)
    try:
        result = build_plan(payload)
    except Exception as exc:
        json.dump({"error": str(exc)}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
