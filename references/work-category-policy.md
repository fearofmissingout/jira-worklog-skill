# Work Category and LLM Baseline Policy

Use this reference when resolving Jira request categories or submitting worklogs for an organization that tracks work type and LLM/Agent time savings.

## Current Work Categories

Prefer the current work-type categories over legacy solution-line categories whenever Jira metadata exposes both.

| Category | Use When | Typical Items |
| --- | --- | --- |
| 方案与文档 | The main output is formal material, documentation, or a report. | Presales proposal, technical proposal, delivery document, design document, weekly report, presentation material, acceptance material, test report |
| 会议与沟通 | The main work is synchronizing information, confirming decisions, or building consensus. | Customer meeting, internal meeting, requirement discussion, technical review, change discussion, project meeting, issue sync |
| 咨询与分析 | The main work is judgment, analysis, advice, or planning. | Consulting, requirement analysis, risk analysis, security assessment, current-state research, technology selection, option comparison |
| 开发测试与验证 | The main work is implementation, configuration development, testing, or validation. | Frontend development, backend development, API development, script development, test cases, feature testing, integration testing, defect validation |
| 项目实施与迁移 | The main work is one-off project delivery, deployment, migration, go-live, or initialization. | System deployment, environment setup, data migration, release, onsite implementation, acceptance support, initial project configuration |
| 日常工单与配置 | The main work is standardized operational requests around resources, permissions, configuration, or data. | Resource provisioning, account permission configuration, parameter adjustment, configuration change, data correction, certificate renewal, policy adjustment, standard service request |
| 变更与问题处理 | The main work is non-standard change, incident, defect, or optimization handling. | Change plan, change execution, troubleshooting, incident fix, defect fix, performance optimization, configuration optimization |
| 进度协调与管理 | The main work is moving tasks forward, coordinating resources, or tracking risks. | Scheduling, progress tracking, resource coordination, risk tracking, to-do follow-up, milestone management, cross-team coordination |

## Classification Rules

Use the user's latest task description first:

- Coding, scripts, APIs, QA, test cases, feature testing, integration testing, validation, defect validation -> `开发测试与验证`.
- Formal output such as proposal, delivery doc, design doc, weekly report, presentation, acceptance material, or test report -> `方案与文档`.
- Meetings, reviews, communication, sync, or consensus-building -> `会议与沟通`.
- Consulting, requirements analysis, risk analysis, assessment, research, technology selection, or option comparison -> `咨询与分析`.
- Deployment, environment setup, migration, release, onsite implementation, acceptance support, or project initialization -> `项目实施与迁移`.
- Resource provisioning, permissions, standard configuration, data correction, certificate renewal, policy adjustment, or standard service requests -> `日常工单与配置`.
- Change execution, troubleshooting, incident/defect fixes, performance optimization, or configuration optimization -> `变更与问题处理`.
- Scheduling, progress tracking, resource coordination, risk tracking, to-do follow-up, milestone management, or cross-team coordination -> `进度协调与管理`.

If a task spans multiple categories, split worklogs only when the user gives separate tasks or hour allocations. Otherwise choose the dominant work type and mention the assumption in the draft.

If Jira metadata no longer exposes one of these values, do not invent it. Use `resolve-issue-fields`, show the available values, and ask the user.

## LLM Baseline Time

Each worklog must include two time concepts:

- Actual time: the normal Jira/Tempo completed time, stored as `hours`.
- Baseline time without LLM/Agent: the time the same work would have taken without LLM/Agent assistance, stored as `without_llm_hours` in plans and submitted through Jira's remaining estimate field.

Rules:

- If the user says they did not use LLM/Agent, set `without_llm_hours = hours`.
- If the user does not mention LLM/Agent use, assume no LLM/Agent was used and set `without_llm_hours = hours`.
- If the user says they used LLM/Agent and gives both actual and baseline time, use those values.
- If the user says they used LLM/Agent but does not give baseline time, ask before submitting.
- If `without_llm_hours < hours`, ask the user to confirm before submitting.

## Jira Submission

When submitting via Jira REST worklog APIs, use the actual time as `timeSpentSeconds` and set the remaining estimate to the baseline time:

```text
POST /rest/api/2/issue/{issueKey}/worklog?adjustEstimate=new&newEstimate=<baseline>
```

Examples:

- 8 actual hours, no LLM/Agent -> `timeSpentSeconds=28800`, `newEstimate=8h`.
- 4 actual hours with LLM/Agent, estimated 8 hours without it -> `timeSpentSeconds=14400`, `newEstimate=8h`.

Because some Jira installations treat remaining estimate as issue-level state rather than per-worklog data, verify the target Jira/Tempo report after first use. If read-back does not expose baseline time but the UI requires it, use browser/UI automation for that field and document the local behavior in `.local/project-rules.local.json`.
