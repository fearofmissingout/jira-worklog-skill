#!/usr/bin/env python3
"""Small Jira/Tempo REST client for the jira-worklog skill.

Credentials are read only from environment variables:
JIRA_BASE_URL, JIRA_USERNAME, JIRA_PASSWORD, optional JIRA_TOKEN.
"""

from __future__ import annotations

import base64
import datetime as dt
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class JiraApiError(RuntimeError):
    def __init__(self, method: str, url: str, status: int | None, body: str):
        self.method = method
        self.url = url
        self.status = status
        self.body = body
        super().__init__(f"{method} {url} failed with {status}: {body[:400]}")


@dataclass
class JiraTempoClient:
    base_url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    @classmethod
    def from_env(cls) -> "JiraTempoClient":
        base_url = os.environ.get("JIRA_BASE_URL")
        username = os.environ.get("JIRA_USERNAME")
        password = os.environ.get("JIRA_PASSWORD")
        token = os.environ.get("JIRA_TOKEN")
        if not base_url:
            raise RuntimeError("Set JIRA_BASE_URL in the environment.")
        if not token and not (username and password):
            raise RuntimeError("Set JIRA_USERNAME/JIRA_PASSWORD or JIRA_TOKEN in the environment.")
        return cls(base_url=base_url, username=username, password=password, token=token)

    def login_session(self) -> dict[str, Any]:
        if not (self.username and self.password):
            raise RuntimeError("Session login requires JIRA_USERNAME and JIRA_PASSWORD.")
        return self.request(
            "POST",
            "/rest/auth/1/session",
            body={"username": self.username, "password": self.password},
            use_basic=False,
        )

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        use_basic: bool = True,
    ) -> Any:
        url = self.base_url + path
        if query:
            filtered = {key: value for key, value in query.items() if value is not None}
            url += "?" + urllib.parse.urlencode(filtered, doseq=True)

        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif use_basic and self.username and self.password:
            raw = f"{self.username}:{self.password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")

        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with self.opener.open(req, timeout=30) as resp:
                payload = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise JiraApiError(method.upper(), url, exc.code, error_body) from exc

        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def myself(self) -> dict[str, Any]:
        return self.request("GET", "/rest/api/2/myself")

    def search_issues(self, jql: str, fields: str = "summary,status,project,issuetype", max_results: int = 50) -> dict[str, Any]:
        return self.request(
            "GET",
            "/rest/api/2/search",
            query={"jql": jql, "fields": fields, "maxResults": max_results},
        )

    def tempo_worklogs(self, date_from: str, date_to: str, username: str) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/rest/tempo-timesheets/3/worklogs",
            query={"dateFrom": date_from, "dateTo": date_to, "username": username},
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("results", "worklogs", "values"):
                if isinstance(result.get(key), list):
                    return result[key]
        return []

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        category: str | None = None,
        category_field: str = "customfield_13900",
        description: str | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if description:
            fields["description"] = description
        if category:
            fields[category_field] = {"value": category}
        return self.request("POST", "/rest/api/2/issue", body={"fields": fields})

    def add_worklog(
        self,
        issue_key: str,
        date: str,
        hours: float,
        comment: str,
        timezone: str = "+0800",
        adjust_estimate: str = "leave",
    ) -> dict[str, Any]:
        seconds = int(round(hours * 3600))
        started = f"{date}T00:00:00.000{timezone}"
        return self.request(
            "POST",
            f"/rest/api/2/issue/{urllib.parse.quote(issue_key)}/worklog",
            query={"adjustEstimate": adjust_estimate},
            body={
                "comment": comment,
                "started": started,
                "timeSpentSeconds": seconds,
            },
        )

    def issue_worklogs(self, issue_key: str) -> dict[str, Any]:
        return self.request("GET", f"/rest/api/2/issue/{urllib.parse.quote(issue_key)}/worklog")


def derive_project_key(issue_key: str) -> str:
    if "-" not in issue_key:
        return ""
    return issue_key.rsplit("-", 1)[0]


def parse_day(day: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(day)
    except ValueError:
        return None


def weekday_label(day: str) -> str:
    parsed = parse_day(day)
    if parsed is None:
        return ""
    return WEEKDAY_LABELS[parsed.weekday()]


def iso_week_key(day: str) -> tuple[int, int] | None:
    parsed = parse_day(day)
    if parsed is None:
        return None
    year, week, _ = parsed.isocalendar()
    return year, week


def project_from_tempo_issue(issue: dict[str, Any], issue_key: str) -> tuple[str, str]:
    project = issue.get("project") or {}
    project_key = (
        project.get("key")
        or issue.get("projectKey")
        or issue.get("project_key")
        or derive_project_key(issue_key)
    )
    project_name = project.get("name") or issue.get("projectName") or issue.get("project_name") or ""
    return str(project_key or ""), str(project_name or "")


def fetch_issue_details(client: Any, issue_keys: list[str]) -> dict[str, dict[str, str]]:
    if not issue_keys:
        return {}
    quoted_keys = ", ".join(f'"{key}"' for key in sorted(set(issue_keys)))
    result = client.search_issues(
        f"key in ({quoted_keys})",
        fields="summary,project",
        max_results=len(set(issue_keys)),
    )
    details: dict[str, dict[str, str]] = {}
    for issue in result.get("issues", []):
        fields = issue.get("fields") or {}
        project = fields.get("project") or {}
        issue_key = issue.get("key") or ""
        details[issue_key] = {
            "issue_summary": fields.get("summary") or "",
            "project_key": project.get("key") or derive_project_key(issue_key),
            "project_name": project.get("name") or "",
        }
    return details


def summarize_tempo_worklogs(
    worklogs: list[dict[str, Any]],
    issue_details: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    issue_details = issue_details or {}
    totals: dict[tuple[str, str], float] = {}
    summaries: dict[str, str] = {}
    project_keys: dict[str, str] = {}
    project_names: dict[str, str] = {}
    issue_weeks: dict[str, set[tuple[int, int]]] = {}
    for worklog in worklogs:
        date_started = str(worklog.get("dateStarted", ""))[:10]
        issue = worklog.get("issue") or {}
        issue_key = issue.get("key") or "<unknown>"
        week_key = iso_week_key(date_started)
        if week_key is not None:
            issue_weeks.setdefault(issue_key, set()).add(week_key)
        details = issue_details.get(issue_key, {})
        tempo_project_key, tempo_project_name = project_from_tempo_issue(issue, issue_key)
        summaries[issue_key] = details.get("issue_summary") or issue.get("summary") or summaries.get(issue_key, "")
        project_keys[issue_key] = details.get("project_key") or tempo_project_key
        project_names[issue_key] = details.get("project_name") or tempo_project_name
        totals[(date_started, issue_key)] = totals.get((date_started, issue_key), 0.0) + (
            float(worklog.get("timeSpentSeconds") or 0) / 3600.0
        )

    rows = []
    for (day, issue_key), hours in sorted(totals.items()):
        issue_compliance = "合规"
        if issue_key == "<unknown>":
            issue_compliance = "未知：缺少issue"
        elif len(issue_weeks.get(issue_key, set())) > 1:
            issue_compliance = "不合规：issue跨周"
        rows.append(
            {
                "date": day,
                "weekday": weekday_label(day),
                "project_key": project_keys.get(issue_key, ""),
                "project_name": project_names.get(issue_key, ""),
                "issue_key": issue_key,
                "issue_summary": summaries.get(issue_key, ""),
                "hours": round(hours, 2),
                "issue_compliance": issue_compliance,
            }
        )
    return rows
