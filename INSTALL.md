# Installation

## Prerequisites

- Git
- Python 3.10 or newer
- Codex desktop or Codex CLI with local skills support
- Jira/Tempo account with REST API access

No third-party Python packages are required.

## Install as a Codex Skill

### Windows PowerShell

```powershell
$skillDir = "$env:USERPROFILE\.codex\skills\jira-worklog"
git clone https://github.com/fearofmissingout/jira-worklog-skill.git $skillDir
```

If the directory already exists:

```powershell
cd "$env:USERPROFILE\.codex\skills\jira-worklog"
git pull
```

### macOS/Linux

```bash
git clone https://github.com/fearofmissingout/jira-worklog-skill.git "$HOME/.codex/skills/jira-worklog"
```

If the directory already exists:

```bash
cd "$HOME/.codex/skills/jira-worklog"
git pull
```

Restart Codex or open a new session so the skill metadata is loaded.

## Optional Automation Setup

Installation does not create recurring jobs automatically. After the skill is installed, ask Codex to initialize automation:

```text
用 jira-worklog 初始化每日工时自动化：10点询问计划，17点生成草稿，18点如果没有风险就自动提交，周末和月末做review。
```

Codex should confirm:

- whether 18:00 auto-submit is enabled;
- whether the default 10:00 / 17:00 / 18:00 local-time schedule is acceptable;
- whether the workflow should run only on confirmed workdays;
- whether any upcoming holidays, leave days, or makeup workdays are known.

Daily operation after setup:

- 10:00: ask for today's project, task, and hours.
- 17:00: show a draft using `日期 | 星期几 | 项目编号 | 项目 | issue | issue名字 | 工时 | issue是否合规`.
- 18:00: submit only if auto-submit is enabled and the draft is clean; otherwise ask for confirmation.
- Last workday of the week: review missing, duplicate, overfilled, and cross-week issue records.
- Last calendar day of the month: review monthly totals, missing days, calendar exceptions, and issue compliance.

## Configure Credentials

Set credentials in your shell environment. Do not write real secrets into repository files.

### Windows PowerShell

```powershell
$env:JIRA_BASE_URL = "https://jira.example.com"
$env:JIRA_USERNAME = "your.username"
$env:JIRA_PASSWORD = "your-password"
```

Optional:

```powershell
$env:JIRA_TOKEN = "your-token"
$env:JIRA_DEFAULT_CATEGORIES_JSON = '{"PROJECTKEY":"Category Name"}'
```

### macOS/Linux

```bash
export JIRA_BASE_URL="https://jira.example.com"
export JIRA_USERNAME="your.username"
export JIRA_PASSWORD="your-password"
```

Optional:

```bash
export JIRA_TOKEN="your-token"
export JIRA_DEFAULT_CATEGORIES_JSON='{"PROJECTKEY":"Category Name"}'
```

## Verify Installation

Run tests:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\tests\test_plan_worklogs.py"
```

Check CLI help:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" --help
```

Check Jira authentication:

```powershell
python "$env:USERPROFILE\.codex\skills\jira-worklog\scripts\jira_worklog_cli.py" me
```

## Uninstall

Remove the skill directory:

```powershell
Remove-Item -LiteralPath "$env:USERPROFILE\.codex\skills\jira-worklog" -Recurse -Force
```

On macOS/Linux:

```bash
rm -rf "$HOME/.codex/skills/jira-worklog"
```
