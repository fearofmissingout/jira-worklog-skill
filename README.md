# Jira Worklog Skill

A Codex skill for drafting, checking, creating, and submitting Jira/Tempo worklogs from natural-language work summaries.

The skill is built around a safe workflow:

1. Parse the user's work summary into structured intent.
2. Split work into weekly-safe Jira issues.
3. Generate a draft before writing anything.
4. Ask the user to resolve holidays, leave, makeup workdays, required fields, and duplicates.
5. Include actual time plus the no-LLM/Agent baseline time for each worklog.
6. Submit only after explicit approval, or after a pre-configured 18:00 auto-submit gate passes every safety check.
7. Read Jira/Tempo back after submission and verify the result.

No company domains, credentials, private project keys, screenshots, cookies, or HAR/WADL discovery artifacts should be committed to this repository.

## Rules

- Jira issue/ticket drafts must not cross ISO week boundaries.
- A broad weekly task defaults to one issue per week.
- If the user specifies multiple tasks in a day, split them into multiple issue/worklog drafts.
- The fallback is one issue for one week only.
- Default full working day is 8 hours.
- Holidays, leave days, weekends, and makeup workdays must be explicit when ambiguous.
- Existing worklogs must be checked before submission.
- Each worklog must include `without_llm_hours`, the estimated time without LLM/Agent assistance.
- If LLM/Agent use is not mentioned, `without_llm_hours` defaults to actual hours.
- Manual submission requires the exact confirmation phrase `SUBMIT_JIRA_WORKLOGS`.
- Scheduled auto-submit is allowed only when the user opted in during automation setup and the current draft has no questions, blocking errors, duplicate risk, overfilled-day risk, or calendar ambiguity.
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
│   ├── automation-workflow.md
│   ├── jira-tempo-api.md
│   ├── local-configuration.md
│   ├── work-category-policy.md
│   └── worklog-rules.md
├── scripts/
│   ├── jira_tempo_client.py
│   ├── jira_worklog_cli.py
│   ├── plan_worklogs.py
│   └── update_skill.py
└── tests/
    ├── test_issue_field_resolution.py
    ├── test_plan_worklogs.py
    ├── test_tempo_summary.py
    └── test_update_skill.py
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
python -m unittest discover -s "$env:USERPROFILE\.codex\skills\jira-worklog\tests" -v
```

## Check for Updates

Install the skill as a Git clone so future updates are simple:

```powershell
cd "$env:USERPROFILE\.codex\skills\jira-worklog"
python .\scripts\update_skill.py check
python .\scripts\update_skill.py update
```

The updater runs `git fetch` and `git pull --ff-only` for Git-installed skills. It refuses to update non-Git copies or directories with local Git changes. Private `.local/` files are ignored by Git and are not overwritten.

## Optional Daily Automation

After installing the skill, ask Codex to initialize the automation explicitly:

```text
用 jira-worklog 初始化每日工时自动化：10点询问计划，17点生成草稿，18点如果没有风险就自动提交，20点执行最终兜底，周末和月末做review。
```

The skill should confirm whether 18:00 auto-submit is enabled, whether last-resort weekly/monthly backfill is enabled, whether the default 10:00 / 17:00 / 18:00 / 20:00 schedule is acceptable, and whether any holidays, leave days, or makeup workdays are known.

Daily flow:

- 10:00: ask what the user will work on today.
- 17:00: generate a draft table for review.
- 18:00: submit only if auto-submit is enabled and every safety check passes; otherwise ask for confirmation or missing details.
- 20:00: if weekly/monthly fallback is enabled and the 18:00 pending list is still unanswered, fill eligible gaps and read back.
- Last workday of the week: review the current week.
- Last calendar day of the month: review the current month.
- Optional last-resort backfill: if enabled and the final weekly/monthly checkpoint has no user confirmation or usable work details, fill confirmed workday gaps by mirroring the last recorded compliant issue from the most recent confirmed workday.

The automation does not blindly fill weekends, holidays, leave days, or uncertain dates. If the calendar is unclear, it asks which dates are non-working days and which weekend dates are makeup workdays.

Last-resort backfill can top up partially filled days to 8h, but it must notify the user for each partial-day fill. It still does not overwrite existing rows, fill uncertain dates, skip project issue-rule validation, or reuse an issue across ISO week boundaries.

## Local Private Config

The agent should create and maintain private local config from search, Jira metadata, historical records, and user confirmation. The user should confirm or correct in natural language instead of editing JSON manually.

Ignored local files live under:

```text
.local/calendar.local.json
.local/project-rules.local.json
.local/automation-state.local.json
```

Examples:

```text
初始化 2026 工作日历
```

```text
6月12号年假，9月30号公司提前放假，10月10号正常补班
```

```text
更新项目创建规则，之后这个项目的子分类用某某分类
```

## Usage Examples

Single project day:

```text
某某项目，做某某功能开发，8小时
```

Multiple tasks in one day:

```text
上午某某项目接口联调4小时，下午另一个项目问题排查4小时
```

Leave day:

```text
今天年假，不填工时
```

Makeup workday:

```text
今天虽然周六但补班，某某项目某某功能开发8小时
```

Weekly broad task:

```text
这周某某项目，做某某功能相关开发，每天8小时
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
  "without_llm_hours": 8,
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

## Resolve Required Jira Fields

Before creating a new issue, resolve required Jira fields from current metadata and task text:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" resolve-issue-fields `
  --project-key EXAMPLE `
  --issue-type "Task" `
  --summary "某某功能 QA 验证" `
  --local-rules "$env:USERPROFILE\.codex\skills\jira-worklog\.local\project-rules.local.json"
```

The helper sends Jira payloads as UTF-8 JSON. If REST/API read-back and the issue page show correct Chinese but a dashboard page shows mojibake, inspect that page's display encoding/cache before rewriting records.

## LLM Baseline Time

The organization policy tracks two time values:

- `hours`: actual completed/spent time.
- `without_llm_hours`: estimated time without LLM/Agent assistance.

When no LLM/Agent was used, or the user does not mention it, these two values are the same. When LLM/Agent was used, ask for the no-LLM baseline before submitting.

The submit helper writes actual time to Jira worklog spent time and writes `without_llm_hours` through Jira remaining estimate:

```text
adjustEstimate=new&newEstimate=<without_llm_hours>
```

See `references/work-category-policy.md` for the current work categories and examples.

## Check Existing Tempo Worklogs

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" check-tempo `
  --from 2026-05-18 `
  --to 2026-05-29 `
  --username your.username
```

Each `rows` entry includes:

- `date`
- `weekday`
- `project_key` as the project number/key
- `project_name`
- `issue_key`
- `issue_summary`
- `hours`
- `issue_compliance`

When presenting results to a user, use this table format:

```text
日期 | 星期几 | 项目编号 | 项目 | issue | issue名字 | 工时 | issue是否合规
```

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
