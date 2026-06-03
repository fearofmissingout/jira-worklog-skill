# Automation Workflow

Use this reference when the user asks to initialize, explain, review, or change recurring worklog automations.

## Setup Principle

Do not create automations during clone/install. The user must explicitly ask to initialize automations after the skill is installed.

Recommended user prompt:

```text
用 jira-worklog 初始化每日工时自动化：10点询问计划，17点生成草稿，18点如果没有风险就自动提交，20点执行最终兜底，周末和月末做review。
```

Before creating or updating an automation, confirm:

- whether 18:00 auto-submit is enabled;
- whether last-resort weekly/monthly backfill is enabled;
- whether 10:00, 17:00, 18:00, and 20:00 local time are acceptable;
- whether the workflow should run only on confirmed workdays;
- whether LLM/Agent baseline time should default to actual time when not mentioned;
- whether any upcoming holidays, leave days, or makeup workdays are already known.
- whether local calendar and project issue-rule config should be initialized or refreshed by the agent.

Prefer one controller automation in the active thread. Avoid creating separate reminder jobs for each checkpoint if a single thread automation can route by current local time.

## Daily Operation

### 10:00 Intake

Ask one short question:

```text
今天做哪些项目/任务？每项大概几小时？如果用了 LLM/Agent，大概相当于不用它要花几小时？
```

Accept casual answers and normalize them into project/task/hour records.

If the user does not mention LLM/Agent, set `without_llm_hours` equal to actual hours. If the user says LLM/Agent was used but does not provide baseline time, keep the draft blocked until clarified.

Examples:

```text
某某项目，做某某功能开发，8小时
```

```text
上午某某项目接口联调4小时，下午另一个项目问题排查4小时
```

```text
今天年假，不填工时
```

```text
今天虽然周六但补班，某某项目某某功能开发8小时
```

### 17:00 Draft

Generate a safe draft, then show the standard table:

```text
日期 | 星期几 | 项目编号 | 项目 | issue | issue名字 | 工时 | issue是否合规
```

Also show comments, questions, and blocking errors when they exist.
Also show actual hours and `without_llm_hours` for each draft worklog when asking for confirmation.

Default issue strategy:

- If the user gives explicit per-day or per-task work, prefer one issue per day or task.
- If the user gives one broad weekly task, one issue for that ISO week is acceptable.
- Never let one issue cross an ISO week boundary.

### 18:00 Auto-Submit Gate

If auto-submit is disabled, ask for explicit confirmation.

If auto-submit is enabled, submit only when all checks are clean:

- latest draft exists for the target date;
- user has not rejected or edited the draft after it was shown;
- no questions or blocking errors remain;
- date is a confirmed workday;
- existing Tempo rows do not indicate duplicate or overfilled worklogs;
- project, issue, issue summary, hours, and comment match the latest user description;
- every worklog has `without_llm_hours`;
- issue compliance is `合规`.

After submission, immediately run a read-back check for the same date and compare the result against the draft.

If any check fails, do not submit. Ask the smallest necessary question.

At 18:00 weekly/monthly review time, show any pending last-resort backfill list. Do not execute weekly/monthly fallback at 18:00. Persist enough state for the 20:00 checkpoint when local state storage is available.

### 20:00 Final Backfill Gate

At 20:00, execute last-resort weekly/monthly backfill only when:

- last-resort backfill is enabled;
- the 18:00 review already showed the pending fill list;
- the user has not confirmed, rejected, corrected, or supplied usable work details since the 18:00 list;
- local calendar marks each target date as a confirmed workday;
- local project rules and Jira metadata allow safe issue creation or reuse;
- duplicate and overfilled checks are clean.

After any 20:00 fallback submission, immediately read Jira/Tempo back and notify the user with the standard table plus a concise audit summary.

## Holiday, Leave, and Makeup Workdays

Default assumptions:

- Weekends are non-working days unless confirmed as makeup workdays.
- Public holidays are non-working days when the relevant schedule is known.
- User-stated leave days are non-working days.
- Makeup workdays count as normal workdays only after confirmation or reliable schedule evidence.

Ask when ambiguous:

```text
这些日期我不确定是否需要填工时：YYYY-MM-DD, YYYY-MM-DD。哪些是不工作日？哪些周末是补班？
```

Never fill a holiday, weekend, or uncertain date merely because it appears in a date range.

Use [local-configuration.md](local-configuration.md) for the agent-managed `.local/calendar.local.json` flow. The user should confirm or correct natural-language calendar summaries; do not require them to edit JSON manually.

## Weekly Review

On the last confirmed workday of the week, after the daily flow, check the current week's Tempo rows.

Report:

- missing workdays;
- dates below or above expected hours;
- duplicate-looking rows;
- issue records that cross week boundaries;
- missing project number, project name, issue, or issue summary;
- records whose project or issue does not match the user's described work.

Use the standard table first, then a concise summary of issues to fix.

If last-resort backfill is enabled and weekly gaps remain, the 18:00 review should show the pending fill list. If the user gives no confirmation or usable work details by 20:00, fill eligible dates by mirroring the last recorded compliant issue from the most recent confirmed workday. If no compliant prior issue exists, stop and ask.

## Monthly Review

On the last calendar day of the month, after the daily flow, check the whole month's Tempo rows.

Report:

- expected workdays versus filled workdays;
- total hours versus expected total;
- missing dates;
- weekend or holiday rows that need confirmation;
- overfilled dates;
- issue compliance problems;
- project-level hour totals.

Do not automatically edit historical worklogs during review. Show findings and ask for confirmation before creating, changing, or deleting anything.

If last-resort backfill is enabled and monthly gaps remain, the 18:00 review should show the pending fill list. If the user gives no confirmation or usable work details by 20:00, fill eligible dates by mirroring the last recorded compliant issue from the nearest prior confirmed workday. Do not overwrite or adjust existing rows.

## Last-Resort Backfill

This is the fallback after daily reminders, daily auto-submit, weekly review, and monthly review all failed to get usable user input. It must be explicitly enabled during automation setup and executes only at the 20:00 final checkpoint.

Trigger it only when:

- the scheduled weekly or monthly final checkpoint has arrived;
- the 18:00 review already showed the pending fill list;
- the user has not confirmed, rejected, or provided task details;
- Tempo shows one or more missing or partially filled expected workdays in the target week or month;
- the missing dates are confirmed workdays.

How to fill:

- Query the nearest prior filled period for this user.
- Pick the last recorded compliant issue from the most recent confirmed workday, moving backward if needed.
- If that day has multiple issues, use the last recorded/created compliant issue only.
- Copy that issue's project, issue-field pattern, summary/task pattern, and comment style for eligible dates.
- Keep issue boundaries inside the target ISO week; create a new weekly/day issue when reusing the old issue would cross a week.
- For zero-hour dates, fill 8h.
- For partially filled dates under 8h, fill the remaining hours to 8h and notify the user for each partial-day fill.
- Do not fill dates already at or above 8h.
- Submit only when duplicate, overfilled-day, required-field, and issue-compliance checks are clean.
- Immediately read Tempo back and report the standard table.

Stop and ask instead of filling when:

- any missing date might be a holiday, leave day, weekend, or uncertain makeup day;
- local calendar or project rules are missing and cannot be initialized from authoritative sources plus user confirmation;
- the latest prior issue has a non-compliant issue, missing project number, missing issue summary, missing assignee/self rule, missing category/subcategory, or ambiguous project;
- copying the prior pattern would cross an ISO week boundary;
- Jira metadata conflicts with local project rules.

Example fallback notice:

```text
18:00 检查到本周仍有待补工时。我会等到 20:00；如果仍无回应且兜底已开启，只会为确认工作日按最近确认工作日的最后一个合规 issue 补齐到 8h。节假日、请假日、周末和不确定调休日不会填。
```

## Public Documentation Hygiene

Use anonymized wording in docs and examples:

- `某某项目`
- `某某功能`
- `EXAMPLE`
- `PROJECTKEY`
- `https://jira.example.com`

Do not include private company names, client names, real domains, real project keys, category mappings, credentials, screenshots, cookies, HAR files, WADL files, or local draft files.
