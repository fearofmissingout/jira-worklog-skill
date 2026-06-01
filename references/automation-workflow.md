# Automation Workflow

Use this reference when the user asks to initialize, explain, review, or change recurring worklog automations.

## Setup Principle

Do not create automations during clone/install. The user must explicitly ask to initialize automations after the skill is installed.

Recommended user prompt:

```text
用 jira-worklog 初始化每日工时自动化：10点询问计划，17点生成草稿，18点如果没有风险就自动提交，周末和月末做review。
```

Before creating or updating an automation, confirm:

- whether 18:00 auto-submit is enabled;
- whether last-resort weekly/monthly backfill is enabled;
- whether 10:00, 17:00, and 18:00 local time are acceptable;
- whether the workflow should run only on confirmed workdays;
- whether any upcoming holidays, leave days, or makeup workdays are already known.

Prefer one controller automation in the active thread. Avoid creating separate reminder jobs for each checkpoint if a single thread automation can route by current local time.

## Daily Operation

### 10:00 Intake

Ask one short question:

```text
今天做哪些项目/任务？每项大概几小时？
```

Accept casual answers and normalize them into project/task/hour records.

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
- issue compliance is `合规`.

After submission, immediately run a read-back check for the same date and compare the result against the draft.

If any check fails, do not submit. Ask the smallest necessary question.

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

If last-resort backfill is enabled and the user gives no confirmation or usable work details by the final weekly checkpoint, fill only missing confirmed workdays by mirroring the latest compliant prior issue/worklog pattern. Prefer the previous week's same project/task pattern when available. If no compliant prior pattern exists, stop and ask.

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

If last-resort backfill is enabled and the user gives no confirmation or usable work details by the final monthly checkpoint, fill only missing confirmed workdays by mirroring the latest compliant prior issue/worklog pattern from the nearest prior filled period. Do not overwrite or adjust existing rows.

## Last-Resort Backfill

This is the fallback after daily reminders, daily auto-submit, weekly review, and monthly review all failed to get usable user input. It must be explicitly enabled during automation setup.

Trigger it only when:

- the scheduled weekly or monthly final checkpoint has arrived;
- the user has not confirmed, rejected, or provided task details;
- Tempo shows one or more missing expected workdays in the target week or month;
- the missing dates are confirmed workdays.

How to fill:

- Query the nearest prior filled period for this user.
- Pick the latest compliant issue/worklog pattern with project number, project name, issue, issue summary, hours, and comment.
- Copy that pattern only as a draft plan for missing confirmed workdays.
- Keep issue boundaries inside the target ISO week; create a new weekly/day issue when reusing the old issue would cross a week.
- Use the default full-day 8h only for dates with zero existing hours.
- Submit only when duplicate, overfilled-day, required-field, and issue-compliance checks are clean.
- Immediately read Tempo back and report the standard table.

Stop and ask instead of filling when:

- any missing date might be a holiday, leave day, weekend, or uncertain makeup day;
- existing worklogs already partially fill the date and the remaining hours are unclear;
- the latest prior pattern has a non-compliant issue, missing project number, missing issue summary, or ambiguous project;
- copying the prior pattern would cross an ISO week boundary;
- more than one plausible prior project/task pattern exists and there is no clear latest pattern.

Example fallback notice:

```text
本周没有收到可用工时信息。我会按已开启的兜底规则，仅为确认工作日中缺失的日期，参考最近一次合规的某某项目/某某功能记录补齐；节假日、请假日、周末和不确定调休日不会填。
```

## Public Documentation Hygiene

Use anonymized wording in docs and examples:

- `某某项目`
- `某某功能`
- `EXAMPLE`
- `PROJECTKEY`
- `https://jira.example.com`

Do not include private company names, client names, real domains, real project keys, category mappings, credentials, screenshots, cookies, HAR files, WADL files, or local draft files.
