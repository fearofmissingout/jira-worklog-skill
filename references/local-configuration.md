# Local Configuration

Use this reference when initializing or updating private local data for calendars, project issue rules, or automation state.

## Storage

Keep private files under the installed skill directory:

```text
.local/calendar.local.json
.local/project-rules.local.json
.local/automation-state.local.json
```

The `.local/` directory must stay ignored by Git. Do not commit real company calendars, personal leave, project keys, issue-field values, usernames, cookies, drafts, or automation state.

## User Experience

The user should not hand-edit JSON. The agent should:

1. Ask for a short natural-language intent.
2. Search or query the relevant source.
3. Generate or update the local JSON file.
4. Show a concise summary.
5. Ask the user to confirm or correct in natural language.
6. Save the confirmed local config.

Example prompts:

```text
初始化 2026 工作日历
```

```text
更新项目创建规则，之后这个项目的子分类用某某分类
```

```text
6月12号年假，9月30号公司提前放假，10月10号正常补班
```

## Work Calendar

Recommended schema:

```json
{
  "region": "CN",
  "year": 2026,
  "official_non_workdays": [],
  "official_extra_workdays": [],
  "company_non_workdays": [],
  "company_extra_workdays": [],
  "personal_leave_days": []
}
```

Resolution priority:

1. User's current explicit instruction.
2. Company or Jira current metadata/configuration.
3. User's historical compliant records.
4. Official holiday and makeup schedule.
5. Default Monday-Friday workday rule.

For official holidays, the agent should search for authoritative current sources before generating the yearly calendar. If sources disagree or the source is not authoritative enough, ask the user before using those dates.

Confirmed workday logic:

- `personal_leave_days` always means non-workday.
- `company_non_workdays` overrides official and default workdays.
- `company_extra_workdays` can make a weekend a confirmed workday.
- `official_non_workdays` and `official_extra_workdays` apply only when company/user overrides are absent.
- An uncertain date can trigger a reminder, but cannot be filled by auto-submit or last-resort backfill.

## Project Issue Rules

Recommended schema:

```json
{
  "PROJECTKEY": {
    "issue_type": "Task",
    "assignee": "self",
    "category_field": "customfield_xxxxx",
    "category": "某某子分类",
    "category_option_id": "12345",
    "summary_template": "{iso_week} {task}",
    "description_template": "{task}",
    "required_fields": {
      "customfield_xxxxx": {"id": "12345", "value": "某某子分类"}
    },
    "field_option_hints": {
      "customfield_xxxxx": {
        "某某子分类": ["开发", "测试", "验证"]
      }
    }
  }
}
```

The agent should discover this from:

- Jira create/edit metadata;
- recent compliant issues in the same project;
- user confirmation or corrections.

Field selection rules:

- Always query current Jira metadata before creating an issue.
- Required option fields must use an `allowedValues` entry from Jira; prefer option `id` payloads over display text.
- Use the user's latest task text to score options. For example, descriptions containing QA, validation, API, coding, debugging, or integration work should favor a development/testing style category over an unrelated historical default.
- Treat local rules and previous issues as weak preferences unless the user explicitly confirms the value in the current turn.
- If a local rule points to a field or option no longer present in Jira metadata, stop and ask before creating.
- After the user corrects a category/subcategory in natural language, update this local file so future runs learn the new rule.

Creation gate:

- Do not create an issue if project rules are missing.
- Do not create an issue if Jira metadata conflicts with local rules.
- Do not create an issue if assignee/self, issue type, category/subcategory, or any required custom field is unclear.
- Show the smallest conflict summary and ask the user to confirm the correct rule.

## Conflict Priority

When sources conflict, prefer:

1. User's current explicit instruction.
2. Company/Jira current metadata.
3. User's historical compliant records.
4. Official calendar.
5. Default Monday-Friday rule.

If the conflict affects submission, issue creation, calendar status, or last-resort backfill, stop and ask before submitting. After the user confirms, update the local config so future runs use the new rule.

## Automation State

Use `.local/automation-state.local.json` for thread-local durable state when needed:

- latest 17:00 draft;
- whether 18:00 review showed a pending 20:00 backfill;
- pending backfill date range and rows;
- timestamps of automatic submissions;
- read-back verification summaries.

Do not use this file as proof that Jira/Tempo was updated. Always read Jira/Tempo back before reporting completion.
