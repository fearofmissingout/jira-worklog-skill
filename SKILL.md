---
name: jira-worklog
description: Use when filling, checking, drafting, creating, validating, automating, checking updates for, or updating Jira and Tempo worklogs from natural-language descriptions, especially daily, weekly, or monthly project work summaries.
---

# Jira Worklog

## Core Rule

Create safe drafts first, ask when holidays or required fields are unclear, submit only after explicit user confirmation or a previously configured safe auto-submit gate, then query Jira/Tempo again to verify.

## Required Flow

1. Parse the user's natural language into structured intent:
   - date range
   - project/client keywords
   - task descriptions
   - hours per day or per task
   - holidays, leave days, makeup workdays, or unknown calendar dates
2. Resolve project and issue candidates with Jira search before creating anything.
3. Resolve Jira issue-create metadata with `scripts/jira_worklog_cli.py resolve-issue-fields` before creating an issue. Use the user's current task text, Jira allowed values, required fields, local project rules, and recent compliant history. Treat local defaults as weak preferences unless the user explicitly confirmed them for this run.
4. Plan worklogs with `scripts/plan_worklogs.py`.
5. Show the draft table to the user:
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
6. Do not submit while any question or blocking error remains.
7. After the user explicitly approves, submit with `scripts/jira_worklog_cli.py submit-plan --confirm SUBMIT_JIRA_WORKLOGS`.
8. Immediately run a read-back check and compare the submitted result against the draft.
9. For organization work categories or LLM/Agent baseline time requirements, read [references/work-category-policy.md](references/work-category-policy.md).
10. For scheduled reminders, daily auto-submit, weekly review, or monthly review, read [references/automation-workflow.md](references/automation-workflow.md) before creating or updating automations.
11. For calendar setup, project issue-field rules, or local automation state, read [references/local-configuration.md](references/local-configuration.md). Generate local config from search/Jira/history plus user confirmation; do not ask users to hand-edit JSON.
12. For "check skill updates", "update this skill", or similar requests, use `scripts/update_skill.py`.

## Worklog Rules

Read [references/worklog-rules.md](references/worklog-rules.md) before planning or submitting. The non-negotiable rules are:

- Issue/ticket must not cross ISO natural week boundaries.
- If the user gives one broad weekly task, default to one issue per week.
- If the user specifies different daily tasks or multiple tasks in a day, split by those tasks.
- The lowest acceptable fallback is one issue, but only within one week.
- Default full working day is 8h.
- Each planned worklog must include `without_llm_hours`. If the user does not mention LLM/Agent use, default `without_llm_hours` to the actual worklog hours. If the user says LLM/Agent was used and does not give the no-LLM baseline, ask before submitting.
- Do not write worklogs for holidays, weekends, leave days, or uncertain dates without user confirmation.
- If the calendar is ambiguous, ask which dates are non-working days and which weekend dates are makeup workdays.
- Check existing worklogs before submitting to avoid duplicates and overfilled days.

## Automation Workflow

Do not create automations during clone/install. Initialize them only when the user explicitly asks, such as "initialize daily Jira worklog automation" or "初始化每日工时自动化".

Use one controller automation for the current thread when possible:

- 10:00 local time: ask what the user will work on today.
- 17:00 local time: turn the user's description into a draft and show the standard table.
- 18:00 local time: if the user opted into auto-submit and the draft is clean, submit and immediately read back; otherwise ask for confirmation or missing details.
- 20:00 local time: if the final weekly/monthly backfill draft is still unanswered and last-resort backfill is enabled, fill eligible gaps and read back.
- Last workday of the week: review the current week's Tempo rows and highlight missing, duplicate, overfilled, or cross-week issue records.
- Last calendar day of the month: review the current month's Tempo rows with the same checks plus month-level totals.
- If the user explicitly enabled last-resort backfill, the last weekly/monthly review prepares a pending backfill at 18:00 and may execute it at 20:00.

At automation setup time, confirm:

- whether 18:00 auto-submit is enabled;
- whether last-resort weekly/monthly backfill is enabled;
- whether the default 10:00 / 17:00 / 18:00 / 20:00 schedule is acceptable;
- which holidays, leave days, or makeup workdays are known if the upcoming period is ambiguous.

Auto-submit at 18:00 is allowed only when all are true:

- the user previously opted into this behavior;
- there is a single latest draft for the target day;
- no questions or blocking errors remain;
- existing Tempo rows do not show duplicate or overfilled worklogs;
- project, issue, issue summary, hours, and comments match the user's latest description;
- the date is a confirmed workday.

Last-resort backfill is allowed only when all are true:

- the user explicitly opted into weekly/monthly backfill;
- the 18:00 weekly/monthly review showed a pending backfill list;
- the 20:00 final checkpoint arrived without user confirmation, rejection, or usable work details;
- missing and partially filled confirmed workdays are filled only up to the expected daily 8h total;
- holidays, leave days, weekends, and uncertain makeup days are excluded;
- the reference source is the last recorded compliant issue from the most recent confirmed workday, moving backward if needed;
- project rules from local config and Jira metadata confirm required create-issue fields, assignee, issue type, and category/custom fields;
- each created or reused issue still stays inside one ISO week;
- no existing Tempo row for the target date would become duplicated or overfilled.

Use generic examples in public docs and prompts, such as "某某项目", "某某功能开发", and "EXAMPLE". Do not include private company names, client names, domains, project names, project keys, categories, credentials, screenshots, cookies, HAR files, or local drafts.

## Issue Field Resolution

Before creating a ticket, run metadata resolution for the target project and issue type. Required option fields such as category/subcategory must be selected from Jira `allowedValues`; do not hard-code a value only because a prior issue used it. The resolver scores the user's latest task text against allowed option names, [work category policy](references/work-category-policy.md), and generic keyword hints, then uses local project rules only as a tie-breaker. If multiple options remain plausible, ask the user and save the confirmed answer under `.local/project-rules.local.json`.

For current organization work categories, prefer work-type categories such as `方案与文档`, `会议与沟通`, `咨询与分析`, `开发测试与验证`, `项目实施与迁移`, `日常工单与配置`, `变更与问题处理`, and `进度协调与管理` over legacy solution-line categories when Jira metadata exposes both.

## LLM Baseline Time

When submitting worklogs, use actual time as completed/spent time and `without_llm_hours` as the Jira remaining estimate. If no LLM/Agent was used or the user does not mention it, set both times equal. If LLM/Agent was used, ask for the hypothetical no-LLM time unless the user already provided it. The REST helper submits this via `adjustEstimate=new&newEstimate=<without_llm_hours>`.

On Windows, keep all JSON files and Python stdout in UTF-8. Avoid sending non-ASCII text through ad hoc PowerShell here-strings or pipes unless `PYTHONIOENCODING=utf-8` is set. The client sends Jira request bodies as UTF-8 JSON with `Content-Type: application/json`; if Jira/Tempo API read-back is correct but a browser page shows mojibake, treat it as a UI/cache/display issue before rewriting data.

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

## Skill Updates

Prefer installing this skill as a Git checkout. When the user asks to check or apply skill updates, run:

```powershell
python .\scripts\update_skill.py check
python .\scripts\update_skill.py update
```

Use `--dir <skill-install-dir>` when running from outside the installed skill directory. The updater only changes Git-tracked skill files. Keep private state under `.local/`, which is ignored by Git.

If the installed skill directory is not a Git checkout, do not overwrite it silently. Tell the user to migrate the installation to a Git clone first, preserving `.local/`.

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
  "without_llm_hours": 8,
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
python .\scripts\jira_worklog_cli.py resolve-issue-fields --project-key EXAMPLE --issue-type Task --summary "Feature QA validation" --local-rules .\.local\project-rules.local.json
python .\scripts\jira_worklog_cli.py check-tempo --from 2026-05-18 --to 2026-05-29 --username <jira-username>
python .\scripts\jira_worklog_cli.py submit-plan --plan plan.json --confirm SUBMIT_JIRA_WORKLOGS
```

`check-tempo` rows must be reported to the user as a table with these columns in order:

```text
日期 | 星期几 | 项目编号 | 项目 | issue | issue名字 | 工时 | issue是否合规
```

The JSON fields are `date`, `weekday`, `project_key`, `project_name`, `issue_key`, `issue_summary`, `hours`, and `issue_compliance`.

Only run `submit-plan` after showing the draft and receiving explicit approval from the user.

For a pre-authorized 18:00 auto-submit workflow, pass the confirmation phrase only after the automation has verified every auto-submit gate listed above.

## Common Mistakes

- Do not create one issue covering multiple weeks.
- Do not fill every weekday blindly when the date range may include holidays, leave, or makeup days.
- Do not submit if required create-issue fields are missing.
- Do not use `adjustEstimate=leave` for organization-compliant submissions when `without_llm_hours` is required; submit `newEstimate` from the planned baseline time and verify the target Jira/Tempo behavior.
- Do not claim completion before a fresh read-back check.
