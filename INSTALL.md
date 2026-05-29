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
