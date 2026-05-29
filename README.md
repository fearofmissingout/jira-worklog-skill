# Jira Worklog Skill

A Codex skill for drafting, checking, creating, and submitting Jira/Tempo worklogs from natural-language work summaries.

The skill is built around a safe workflow:

1. Parse the user's work summary into structured intent.
2. Split work into weekly-safe Jira issues.
3. Generate a draft before writing anything.
4. Ask the user to resolve holidays, leave, makeup workdays, required fields, and duplicates.
5. Submit only after explicit approval.
6. Read Jira/Tempo back after submission and verify the result.

No company domains, credentials, private project keys, screenshots, cookies, or HAR/WADL discovery artifacts should be committed to this repository.

## Rules

- Jira issue/ticket drafts must not cross ISO week boundaries.
- A broad weekly task defaults to one issue per week.
- If the user specifies multiple tasks in a day, split them into multiple issue/worklog drafts.
- The fallback is one issue for one week only.
- Default full working day is 8 hours.
- Holidays, leave days, weekends, and makeup workdays must be explicit when ambiguous.
- Existing worklogs must be checked before submission.
- Submission requires the exact confirmation phrase `SUBMIT_JIRA_WORKLOGS`.
- Completion requires read-back verification from Jira/Tempo.

## Repository Layout

```text
.
├── SKILL.md
├── INSTALL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── jira-tempo-api.md
│   └── worklog-rules.md
├── scripts/
│   ├── jira_tempo_client.py
│   ├── jira_worklog_cli.py
│   └── plan_worklogs.py
└── tests/
    └── test_plan_worklogs.py
```

## Quick Start

Clone into your Codex skills directory:

```powershell
git clone https://github.com/fearofmissingout/jira-worklog-skill.git "$env:USERPROFILE\.codex\skills\jira-worklog"
```

Configure credentials in your shell, not in files:

```powershell
$env:JIRA_BASE_URL = "https://jira.example.com"
$env:JIRA_USERNAME = "your.username"
$env:JIRA_PASSWORD = "your-password"
```

Check authentication:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" me
```

Run tests:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\tests\test_plan_worklogs.py"
```

## Draft a Plan

Create a structured intent file:

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
```

Generate a draft:

```powershell
Get-Content -LiteralPath .\plan-input.json -Raw -Encoding utf8 |
  python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\plan_worklogs.py" |
  Set-Content -LiteralPath .\plan-output.json -Encoding utf8
```

Review `plan-output.json`. Do not submit while `questions` or `blocking_errors` are non-empty.

## Check Existing Tempo Worklogs

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" check-tempo `
  --from 2026-05-18 `
  --to 2026-05-29 `
  --username your.username
```

Each `rows` entry includes:

- `date`
- `project_key` as the project number/key
- `project_name`
- `issue_key`
- `issue_summary`
- `hours`

## Submit a Confirmed Plan

Only run this after the user has reviewed the draft and explicitly approved submission:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" submit-plan `
  --plan .\plan-output.json `
  --confirm SUBMIT_JIRA_WORKLOGS
```

Then run `check-tempo` for the same date range and compare the result against the draft.

## Project Defaults

Some Jira projects require custom fields when creating issues. The planner supports default categories via environment variable:

```powershell
$env:JIRA_DEFAULT_CATEGORIES_JSON = '{"EXAMPLE":"Development"}'
```

Keep private project names, category mappings, and client details out of this public repository. Store them in local environment variables or private notes.

## Security Notes

- Never commit `.env`, cookies, screenshots, HAR files, WADL files, cURL exports, or local drafts.
- Never hard-code credentials in `SKILL.md`, scripts, tests, or docs.
- Prefer tokens over passwords if your Jira supports them.
- Review `git status --short` before every commit.
