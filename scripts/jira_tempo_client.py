#!/usr/bin/env python3
"""Small Jira/Tempo REST client for the jira-worklog skill.

Credentials are read only from environment variables:
JIRA_BASE_URL, JIRA_USERNAME, JIRA_PASSWORD, optional JIRA_TOKEN.
"""

from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


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


def summarize_tempo_worklogs(worklogs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], float] = {}
    summaries: dict[str, str] = {}
    for worklog in worklogs:
        date_started = str(worklog.get("dateStarted", ""))[:10]
        issue = worklog.get("issue") or {}
        issue_key = issue.get("key") or "<unknown>"
        summaries[issue_key] = issue.get("summary") or summaries.get(issue_key, "")
        totals[(date_started, issue_key)] = totals.get((date_started, issue_key), 0.0) + (
            float(worklog.get("timeSpentSeconds") or 0) / 3600.0
        )

    rows = []
    for (day, issue_key), hours in sorted(totals.items()):
        rows.append(
            {
                "date": day,
                "issue_key": issue_key,
                "issue_summary": summaries.get(issue_key, ""),
                "hours": round(hours, 2),
            }
        )
    return rows
