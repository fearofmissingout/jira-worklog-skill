# Jira and Tempo API Reference

This reference intentionally uses generic endpoints and placeholders. Store private domains, project keys, usernames, and category values in local environment variables or private notes, not in this repository.

## Authentication

Common Jira Server options:

- `POST /rest/auth/1/session`
- Basic auth against `GET /rest/api/2/myself`
- Bearer token if your Jira instance supports it

Use environment variables. Do not save credentials in the skill.

## Read User

```text
GET /rest/api/2/myself
```

Use this first to confirm the credential maps to the expected Jira user.

## Search Issues

```text
GET /rest/api/2/search?jql=...&fields=summary,status,project,issuetype&maxResults=...
POST /rest/api/2/search
```

Use search to resolve fuzzy natural-language project/task descriptions to existing issues before creating new tickets.

## Create Issue

```text
POST /rest/api/2/issue
```

Typical fields:

```json
{
  "fields": {
    "project": {"key": "PROJECTKEY"},
    "summary": "2026-W22 Feature development",
    "issuetype": {"name": "Task"}
  }
}
```

Some Jira projects require additional custom fields such as category, request type, component, or customer field. Put non-secret defaults in the plan payload or use `JIRA_DEFAULT_CATEGORIES_JSON`.

## Jira Worklogs

Create:

```text
POST /rest/api/2/issue/{issueKey}/worklog?adjustEstimate=leave
```

Payload:

```json
{
  "comment": "Working on: Feature development",
  "started": "2026-05-29T00:00:00.000+0800",
  "timeSpentSeconds": 28800
}
```

Read:

```text
GET /rest/api/2/issue/{issueKey}/worklog
```

Prefer `adjustEstimate=leave` unless the user explicitly asks to change remaining estimate.

## Tempo Worklogs

Common Tempo Server endpoint:

```text
GET /rest/tempo-timesheets/3/worklogs?dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD&username=<username>
```

Common fields:

- `id`
- `jiraWorklogId`
- `dateStarted`
- `timeSpentSeconds`
- `comment`
- `author`
- `issue.key`
- `issue.summary`
- `issue.project.key` or project key derived from the issue key
- `issue.project.name`, when available or fetched from Jira search
- `worklogAttributes`
- `workAttributeValues`

The CLI enriches Tempo rows with Jira search when possible so output rows include both `project_key` and `project_name`.

Other useful endpoints may exist depending on Tempo version and permissions:

```text
GET /rest/tempo-timesheets/3/worklogs/invalidWorklogs
POST /rest/tempo-timesheets/3/worklogs/validate
POST /rest/tempo-timesheets/4/worklogs/search
POST /rest/tempo-timesheets/4/worklogs/dateAggregatedWorklogs
```

Use Tempo read-back for final verification whenever possible.
