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

Before creating issues, discover and validate project metadata:

```text
GET /rest/api/2/issue/createmeta?projectKeys=PROJECTKEY&expand=projects.issuetypes.fields
GET /rest/api/2/issue/{issueKey}/editmeta
```

Use metadata plus local project rules to confirm issue type, assignee/self support, category/subcategory fields, components, and required custom fields. If metadata conflicts with `.local/project-rules.local.json`, stop and ask the user to confirm the correct rule.

For required option fields, prefer the resolver:

```text
python scripts/jira_worklog_cli.py resolve-issue-fields \
  --project-key PROJECTKEY \
  --issue-type "Task" \
  --summary "Feature QA validation" \
  --description "API validation and data export" \
  --local-rules .local/project-rules.local.json
```

Resolution policy:

1. User's current explicit field/category instruction wins.
2. Jira create/edit metadata controls which fields and allowed values are valid.
3. The current task text is scored against allowed option names and keyword hints.
4. Local project rules and historical compliant issues are weak preferences, not hard-coded answers.
5. If no option is clearly best, stop and ask; after confirmation, update `.local/project-rules.local.json`.

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

Some Jira projects require additional custom fields such as category, request type, component, or customer field. Store project-specific defaults in private local config or environment variables, not public docs.

When creating with resolved fields, pass Jira option ids when available:

```json
{
  "fields": {
    "project": {"key": "PROJECTKEY"},
    "summary": "Feature QA validation",
    "issuetype": {"name": "Task"},
    "assignee": {"name": "current.user"},
    "customfield_10000": {"id": "12345"}
  }
}
```

## Encoding

The helper scripts send request bodies as UTF-8 JSON:

```python
json.dumps(body, ensure_ascii=False).encode("utf-8")
```

Use `Content-Type: application/json`. On Windows, set `PYTHONIOENCODING=utf-8` before printing Chinese JSON to the terminal. If Jira issue pages and Jira/Tempo REST API read-back show correct Chinese but a board/home page shows mojibake, the stored Jira data is probably correct; refresh/clear cache or inspect that page's response encoding before rewriting records.

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

`check-tempo` row output fields:

- `date`
- `weekday`
- `project_key`
- `project_name`
- `issue_key`
- `issue_summary`
- `hours`
- `issue_compliance`

Other useful endpoints may exist depending on Tempo version and permissions:

```text
GET /rest/tempo-timesheets/3/worklogs/invalidWorklogs
POST /rest/tempo-timesheets/3/worklogs/validate
POST /rest/tempo-timesheets/4/worklogs/search
POST /rest/tempo-timesheets/4/worklogs/dateAggregatedWorklogs
```

Use Tempo read-back for final verification whenever possible.
