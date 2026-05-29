---
name: jira-worklog
description: Use when filling, checking, drafting, creating, or validating Jira and Tempo worklogs from natural-language descriptions, especially weekly or daily project work summaries.
---

# Jira Worklog

## Core Rule

Create safe drafts first, ask when holidays or required fields are unclear, submit only after explicit user confirmation, then query Jira/Tempo again to verify.

## Required Flow

1. Parse the user's natural language into structured intent:
   - date range
   - project/client keywords
   - task descriptions
   - hours per day or per task
   - holidays, leave days, makeup workdays, or unknown calendar dates
2. Resolve project and issue candidates with Jira search before creating anything.
3. Plan worklogs with `scripts/plan_worklogs.py`.
4. Show the draft table to the user:
   - date
   - weekday
   - project key / project number
   - project name
   - issue to reuse or issue to create
   - issue summary
   - hours
   - issue compliance
   - comment
   - questions and blocking errors
5. Do not submit while any question or blocking error remains.
6. After the user explicitly approves, submit with `scripts/jira_worklog_cli.py submit-plan --confirm SUBMIT_JIRA_WORKLOGS`.
7. Immediately run a read-back check and compare the submitted result against the draft.

## Worklog Rules

Read [references/worklog-rules.md](references/worklog-rules.md) before planning or submitting. The non-negotiable rules are:

- Issue/ticket must not cross ISO natural week boundaries.
- If the user gives one broad weekly task, default to one issue per week.
- If the user specifies different daily tasks or multiple tasks in a day, split by those tasks.
- The lowest acceptable fallback is one issue, but only within one week.
- Default full working day is 8h.
- Do not write worklogs for holidays, weekends, leave days, or uncertain dates without user confirmation.
- If the calendar is ambiguous, ask which dates are non-working days and which weekend dates are makeup workdays.
- Check existing worklogs before submitting to avoid duplicates and overfilled days.

## Credentials

Never ask the user to paste a password into files. Never save credentials in the skill.

Use environment variables only:

```text
JIRA_BASE_URL=https://jira.example.com
JIRA_USERNAME=<username>
JIRA_PASSWORD=<password>
```

`JIRA_TOKEN` is also supported by the client script if available.

Optional default issue categories can be supplied as JSON:

```text
JIRA_DEFAULT_CATEGORIES_JSON={"PROJECTKEY":"Category Name"}
```

## Planning Script

Pass structured JSON through stdin. On Windows PowerShell, prefer a UTF-8 JSON file or Python-generated JSON for non-ASCII text; avoid ad hoc shell pipes that can corrupt text.

```powershell
@"
{
  "date_from": "2026-05-18",
  "date_to": "2026-05-29",
  "project": {
    "key": "EXAMPLE",
    "name": "Example Project"
  },
  "default_hours": 8,
  "description": "Feature development",
  "category": "Development"
}
"@ | Set-Content -LiteralPath .\plan-input.json -Encoding utf8
Get-Content -LiteralPath .\plan-input.json -Raw -Encoding utf8 | python .\scripts\plan_worklogs.py
```

The script returns `issue_drafts`, `questions`, and `blocking_errors`.

## Jira/Tempo API Helpers

See [references/jira-tempo-api.md](references/jira-tempo-api.md) for endpoint guidance.

Useful commands:

```powershell
python .\scripts\jira_worklog_cli.py me
python .\scripts\jira_worklog_cli.py check-tempo --from 2026-05-18 --to 2026-05-29 --username <jira-username>
python .\scripts\jira_worklog_cli.py submit-plan --plan plan.json --confirm SUBMIT_JIRA_WORKLOGS
```

`check-tempo` rows must be reported to the user as a table with these columns in order:

```text
日期 | 星期几 | 项目编号 | 项目 | issue | issue名字 | 工时 | issue是否合规
```

The JSON fields are `date`, `weekday`, `project_key`, `project_name`, `issue_key`, `issue_summary`, `hours`, and `issue_compliance`.

Only run `submit-plan` after showing the draft and receiving explicit approval from the user.

## Common Mistakes

- Do not create one issue covering multiple weeks.
- Do not fill every weekday blindly when the date range may include holidays, leave, or makeup days.
- Do not submit if required create-issue fields are missing.
- Do not assume UI defaults such as remaining estimate should be changed; worklog submission should use `adjustEstimate=leave` unless the user explicitly says otherwise.
- Do not claim completion before a fresh read-back check.
