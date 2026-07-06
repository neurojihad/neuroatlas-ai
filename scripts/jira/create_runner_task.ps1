#Requires -Version 5.1
<#
.SYNOPSIS
  Create NLS-705 (self-hosted GitLab Runner) and add to active sprint.

.EXAMPLE
  .\scripts\jira\create_runner_task.ps1
  .\scripts\jira\create_runner_task.ps1 -SprintId 68
#>
param(
    [int]$SprintId = 68,
    [switch]$SkipSprintAdd
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"

$EpicOps = "NLS-12"

$Description = @"
## Context
GitLab.com shared runner compute minutes for the neurojihad namespace are exhausted. Pipelines fail until we run CI on a project-owned runner (no shared minutes).

## Architecture reference
docs/ci/self-hosted-runner.md
docs/ci/self-hosted-runner-plan.md
docs/ARCHITECTURE.md section 12

## Acceptance criteria
- [ ] Project runner registered with tag ``neuroatlas-self-hosted``, locked to project, untagged jobs off
- [ ] ``.gitlab-ci.yml`` uses ``default.tags: [neuroatlas-self-hosted]``
- [ ] Registration scripts: ``scripts/ci/register-gitlab-runner.sh`` and ``.ps1``
- [ ] Pipeline green on self-hosted runner (check, unit, migrations at minimum)
- [ ] Shared runners disabled on project after verification

## Docs
- docs/ci/self-hosted-runner.md
"@

Write-Host "Creating story: Self-hosted GitLab Runner (NLS-705)..."
$createOut = & $ApiScript create -Type Story -Summary "Self-hosted GitLab Runner (docker executor, project-locked)" -Epic $EpicOps -Description $Description
$key = ($createOut | Where-Object { $_ -match '^Created: (NLS-\d+)$' } | ForEach-Object { if ($_ -match 'NLS-\d+') { $matches[0] } } | Select-Object -First 1)
if (-not $key) {
    throw "Could not parse Jira key from create output: $createOut"
}
Write-Host "Created: $key"

if (-not $SkipSprintAdd) {
    Write-Host "Adding $key to sprint $SprintId..."
    & $ApiScript sprint-add $SprintId $key
}

Write-Host "Update docs/jira/backlog-keys.md: NLS-705 -> $key"
Write-Host "Done."
