#Requires -Version 5.1
<#
.SYNOPSIS
  Create NeuroAtlas epics, M1 stories, and Sprint 01 "Pioneer" in Jira.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"

function Invoke-JiraApi {
    param(
        [string]$Command,
        [string]$Arg1 = "",
        [string]$Type = "Story",
        [string]$Summary = "",
        [string]$Epic = "",
        [string]$Description = "",
        [int]$BoardId = 0
    )
    $params = @{
        Command = $Command
    }
    if ($Arg1) { $params["Arg1"] = $Arg1 }
    if ($Type) { $params["Type"] = $Type }
    if ($Summary) { $params["Summary"] = $Summary }
    if ($Epic) { $params["Epic"] = $Epic }
    if ($Description) { $params["Description"] = $Description }
    if ($BoardId -gt 0) { $params["BoardId"] = $BoardId }
    & $ApiScript @params
}

function Get-JiraConfigFromScript {
    $root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
    $envFile = Join-Path $root "infra\.env"
    Get-Content -LiteralPath $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        if ($line -match '^\s*([^=]+)=(.*)$') {
            Set-Item -Path ("env:{0}" -f $matches[1].Trim()) -Value $matches[2].Trim()
        }
    }
    $pair = "{0}:{1}" -f $env:JIRA_EMAIL, $env:JIRA_API_TOKEN
    $auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pair))
    @{
        BaseUrl = $env:JIRA_BASE_URL.TrimEnd("/")
        Auth    = $auth
        Project = $env:JIRA_PROJECT_KEY
    }
}

function Invoke-JiraRaw {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )
    $cfg = Get-JiraConfigFromScript
    $headers = @{
        Authorization = "Basic {0}" -f $cfg.Auth
        Accept        = "application/json"
    }
    $params = @{
        Method  = $Method
        Uri     = "{0}{1}" -f $cfg.BaseUrl, $Path
        Headers = $headers
    }
    if ($null -ne $Body) {
        $params["Body"] = ($Body | ConvertTo-Json -Depth 20 -Compress)
        $params["ContentType"] = "application/json"
    }
    Invoke-RestMethod @params
}

$epics = @(
    @{ Ref = "NLS-EPIC-01"; Title = "Microservice foundation" },
    @{ Ref = "NLS-EPIC-02"; Title = "Clinical data (Patients)" },
    @{ Ref = "NLS-EPIC-03"; Title = "Identity & audit" },
    @{ Ref = "NLS-EPIC-04"; Title = "Event backbone" },
    @{ Ref = "NLS-EPIC-05"; Title = "Knowledge base (RAG pipeline)" },
    @{ Ref = "NLS-EPIC-06"; Title = "Machine learning" },
    @{ Ref = "NLS-EPIC-07"; Title = "Observability & ops" },
    @{ Ref = "NLS-EPIC-08"; Title = "Frontend" }
)

$stories = @(
    @{
        Ref = "NLS-301"
        EpicRef = "NLS-EPIC-03"
        Title = "Keycloak realm bootstrap (neuroatlas, roles, client)"
        Description = @"
## Context
Bootstrap Keycloak realm for local and Docker dev.

## Architecture reference
docs/ARCHITECTURE.md section 5 and 6 (Keycloak)

## Acceptance criteria
- [ ] Realm neuroatlas imported with roles and neuroatlas-api client
- [ ] Documented in docs/diagrams/auth-keycloak-user-registration.md
- [ ] make up_infra starts Keycloak with realm ready

## Local ref
docs/jira/plan.md — NLS-301
"@
    },
    @{
        Ref = "NLS-202"
        EpicRef = "NLS-EPIC-02"
        Title = "Alembic migrations: patients + assessments tables"
        Description = @"
## Context
Persist patients and assessments in Postgres via Housekeeper migrations.

## Architecture reference
docs/ARCHITECTURE.md section 4 (Housekeeper)

## Acceptance criteria
- [ ] Alembic revision creates patients and assessments tables
- [ ] Migrations runnable via housekeeper service
- [ ] Schema matches domain entities

## Local ref
docs/jira/plan.md — NLS-202
"@
    },
    @{
        Ref = "NLS-201"
        EpicRef = "NLS-EPIC-02"
        Title = "Patients SQLAlchemy adapter (replace in-memory UoW)"
        Description = @"
## Context
Replace in-memory UnitOfWork with SQLAlchemy/asyncpg adapter. Scaffold may exist (Partial).

## Architecture reference
docs/ARCHITECTURE.md section 12

## Acceptance criteria
- [ ] SQLAlchemy repositories implement domain ports
- [ ] UnitOfWork commits/rolls back via async session
- [ ] patients service runs against Postgres when configured

## Local ref
docs/jira/plan.md — NLS-201 (Partial)
"@
    },
    @{
        Ref = "NLS-302"
        EpicRef = "NLS-EPIC-03"
        Title = "Shadow users table JIT upsert in production path"
        Description = @"
## Context
JIT upsert authenticated users into shadow users table on each request. Scaffold may exist (Partial).

## Architecture reference
docs/ARCHITECTURE.md section 5, docs/diagrams/auth-jit-upsert.md

## Acceptance criteria
- [ ] UserUpsert runs when USER_UPSERT_ENABLED=true
- [ ] Correlates audit events with user_id
- [ ] Integration test covers upsert idempotency

## Local ref
docs/jira/plan.md — NLS-302 (Partial)
"@
    }
)

Write-Output "=== NeuroAtlas Jira bootstrap: epics + Sprint Pioneer ==="

# Map epic ref -> Jira key
$epicKeys = @{}

Write-Output ""
Write-Output "--- Creating epics ---"
foreach ($epic in $epics) {
    $desc = @"
## Epic
$($epic.Ref) — $($epic.Title)

## Backlog
docs/jira/plan.md

## Architecture
docs/ARCHITECTURE.md section 12
"@
    $out = Invoke-JiraApi -Command create -Type Epic -Summary $epic.Title -Description $desc
    $line = ($out | Select-Object -Last 2 | Select-Object -First 1)
    if ($line -match "Created:\s+(\S+)") {
        $key = $Matches[1]
        $epicKeys[$epic.Ref] = $key
        Write-Output ("{0} -> {1}" -f $epic.Ref, $key)
    }
    else {
        throw "Failed to parse epic key from: $out"
    }
}

Write-Output ""
Write-Output "--- Creating Sprint 01 stories (M1) ---"
$storyKeys = @()
foreach ($story in $stories) {
    $epicKey = $epicKeys[$story.EpicRef]
    $out = Invoke-JiraApi -Command create -Type Story -Summary $story.Title -Epic $epicKey -Description $story.Description
    $line = ($out | Select-Object -Last 2 | Select-Object -First 1)
    if ($line -match "Created:\s+(\S+)") {
        $key = $Matches[1]
        $storyKeys += $key
        Write-Output ("{0} -> {1} (epic {2})" -f $story.Ref, $key, $epicKey)
    }
    else {
        throw "Failed to parse story key from: $out"
    }
}

Write-Output ""
Write-Output "--- Resolving scrum board ---"
$boards = Invoke-JiraRaw -Method GET -Path "/rest/agile/1.0/board?projectKeyOrId=$($env:JIRA_PROJECT_KEY)"
if (-not $boards.values -or $boards.values.Count -eq 0) {
    throw "No scrum board found for project $($env:JIRA_PROJECT_KEY). Create a Scrum board in Jira UI first."
}
$boardId = $boards.values[0].id
$boardName = $boards.values[0].name
Write-Output ("Board: {0} (id {1})" -f $boardName, $boardId)

Write-Output ""
Write-Output "--- Creating sprint Pioneer ---"
$sprintBody = @{
    name          = "Pioneer"
    goal          = "M1 - Runnable clinical API: Postgres persistence, Keycloak auth, JIT user upsert"
    originBoardId = $boardId
}
$sprint = Invoke-JiraRaw -Method POST -Path "/rest/agile/1.0/sprint" -Body $sprintBody
Write-Output ("Sprint: {0} (id {1})" -f $sprint.name, $sprint.id)

Write-Output ""
Write-Output "--- Adding stories to sprint ---"
$addBody = @{ issues = $storyKeys }
Invoke-JiraRaw -Method POST -Path ("/rest/agile/1.0/sprint/{0}/issue" -f $sprint.id) -Body $addBody | Out-Null
foreach ($key in $storyKeys) {
    Write-Output ("  + {0}" -f $key)
}

Write-Output ""
Write-Output "=== Done ==="
Write-Output "Sprint goal: M1 - Runnable clinical API"
Write-Output "Stories (dependency order): $($storyKeys -join ', ')"
