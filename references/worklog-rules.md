# Worklog Rules

## Filling Style

The skill is designed for Jira/Tempo workflows where timesheet entries should be planned safely from natural-language summaries.

## Issue Splitting Priority

1. Explicit per-day/per-task instructions from the user win.
   - Example: "Monday API integration 4h, data sync 4h" means two worklogs and likely two issues.
2. Broad weekly instruction defaults to one issue per week.
   - Example: "This week project A development every day 8h" means one weekly issue with five worklogs.
3. Multi-week instruction must be split by ISO week.
   - Example: "Last week and this week project A every day 8h" means two issues.
4. Worst acceptable fallback is one issue for one week only.

## Boundaries

- Never let an issue cover dates from more than one ISO week.
- Worklogs inside an issue must be between that issue's `week_start` and `week_end`.
- A date's total planned worklog hours must not exceed 8h unless the user explicitly approves overtime.
- Default full working day: 8h.
- Do not create or submit anything if duplicate worklogs appear likely.

## Calendar Handling

Use the relevant official holiday/makeup schedule when known, but do not guess uncertain dates.

Ask the user when:

- the date range includes a holiday and the user did not say whether to fill it;
- the date range includes a weekend that may be a makeup workday;
- the user says "last week", "this week", or "this month" around a holiday period and does not specify leave or makeup days;
- existing Tempo data conflicts with the natural-language request.

Useful question wording:

```text
I am not sure whether these dates should receive worklogs: YYYY-MM-DD, YYYY-MM-DD. Which dates were non-working days, and which weekend dates were makeup workdays?
```

## Submission Gate

Before submission, show a draft and require explicit approval. The draft must include:

- issue to reuse or create;
- project key/name;
- issue summary;
- date;
- hours;
- comment;
- questions;
- blocking errors.

After submission, query Tempo/Jira again and verify:

- each expected date has the expected hours;
- no date exceeds the daily limit unexpectedly;
- each issue stays inside one week;
- project and issue match the user's natural-language intent.
