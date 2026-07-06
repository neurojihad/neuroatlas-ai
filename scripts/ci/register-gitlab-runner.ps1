#Requires -Version 5.1
<#
.SYNOPSIS
  Register a GitLab Runner on Windows (docker executor, tag neuroatlas-self-hosted).

.DESCRIPTION
  Requires GitLab Runner installed as a Windows service and Docker Desktop running.

.EXAMPLE
  $env:GITLAB_RUNNER_TOKEN = "glrt-..."
  .\scripts\ci\register-gitlab-runner.ps1
#>
param(
    [string]$GitLabUrl = "https://gitlab.com/",
    [string]$ProjectUrl = "https://gitlab.com/neurojihad/neuroatlas",
    [string]$RunnerTag = "neuroatlas-self-hosted",
    [string]$RunnerName = "neuroatlas-self-hosted",
    [string]$DefaultImage = "python:3.12-slim-bookworm"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$token = if ($env:GITLAB_RUNNER_TOKEN) { $env:GITLAB_RUNNER_TOKEN } else { $null }
if (-not $token) {
    throw "Set GITLAB_RUNNER_TOKEN (GitLab → Settings → CI/CD → Runners → New project runner)."
}

$runnerExe = "gitlab-runner"
if (-not (Get-Command $runnerExe -ErrorAction SilentlyContinue)) {
    throw "gitlab-runner not on PATH. Install: https://docs.gitlab.com/runner/install/windows.html"
}

try {
    docker info 2>&1 | Out-Null
} catch {
    throw "Docker Desktop is not running or not installed."
}

Write-Host "Registering runner '$RunnerName' (tags/lock set in GitLab UI when creating the runner)"

& $runnerExe register `
    --non-interactive `
    --url $GitLabUrl `
    --token $token `
    --executor "docker" `
    --docker-image $DefaultImage `
    --description $RunnerName

Write-Host "Done. Restart service: Restart-Service gitlab-runner"
Write-Host "Verify in GitLab → Settings → CI/CD → Runners"
