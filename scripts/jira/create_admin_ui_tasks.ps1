#Requires -Version 5.1
<#
.SYNOPSIS
  Create admin_ui BFF + React panel stories (NLS-ADMIN-*) and add them to Sprint Pioneer.

.DESCRIPTION
  PaymentGate-style admin_ui service: embedded React SPA, Keycloak OIDC auth handlers,
  guard proxy to backends. Supersedes standalone gateway + Next.js browser path for Pioneer.

.EXAMPLE
  .\scripts\jira\create_admin_ui_tasks.ps1
  .\scripts\jira\create_admin_ui_tasks.ps1 -SprintId 35
#>
param(
    [int]$SprintId = 35,
    [switch]$SkipSprintAdd
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

$EpicGateway = "NLS-6"
$EpicIdentity = "NLS-8"
$EpicPatients = "NLS-7"
$EpicFrontend = "NLS-13"

function New-Desc {
    param(
        [string]$Ref,
        [string]$Context,
        [string[]]$AC,
        [string]$Related = "",
        [string]$Arch = "docs/ARCHITECTURE.md section 5, docs/diagrams/auth-paymentgate-comparison.md"
    )
    $acLines = ($AC | ForEach-Object { "- [ ] $_" }) -join "`n"
    $relatedBlock = ""
    if ($Related) {
        $relatedBlock = "`n## Related / supersedes`n$Related`n"
    }
    return @"
## Context
$Context

Sprint: Pioneer (admin_ui BFF + browser Keycloak auth). Tracker ref: $Ref

## Architecture reference
$Arch

## Acceptance criteria
$acLines
$relatedBlock
## Docs
- docs/diagrams/auth-browser-gateway-flow.md (unified BFF variant)
- docs/diagrams/auth-request-flow.md
- docs/jira/sprint-01-pioneer.md
- PaymentGate reference: paymentgate/src/admin_ui/ (no AtomID exchange in NeuroAtlas)
"@
}

$Tasks = @(
    @{
        Ref   = "NLS-ADMIN-01"
        Epic  = $EpicGateway
        Title = "admin_ui service scaffold (src/admin_ui/, hex layout)"
        Desc  = New-Desc "NLS-ADMIN-01" "FastAPI admin_ui BFF module: main, lifespan, settings, /health. Replaces standalone src/gateway/ for browser entry." @(
            "src/admin_ui/ follows patients service hexagonal layout"
            "make run_admin_ui and test_admin_ui targets documented"
            "Health endpoint returns 200"
        ) "Supersedes plan NLS-GW-01 (Jira NLS-50); decomposes NLS-101"
    },
    @{
        Ref   = "NLS-ADMIN-02"
        Epic  = $EpicIdentity
        Title = "Keycloak browser client neuroatlas-ui (redirect URIs, admin_ui callback)"
        Desc  = New-Desc "NLS-ADMIN-02" "Configure Keycloak public/confidential client for admin_ui authorization code flow." @(
            "Client neuroatlas-ui in infra/keycloak/import/neuroatlas-realm.json"
            "Redirect URI http://localhost:8000/auth/callback (and Docker equivalent)"
            "Web origins for admin_ui on port 8000"
            "Access token aud includes neuroatlas-api"
        ) "Supersedes NLS-GW-03 (Jira NLS-52); extends NLS-301 / NLS-14"
    },
    @{
        Ref   = "NLS-ADMIN-03"
        Epic  = $EpicGateway
        Title = "admin_ui OIDC auth handlers (login, token, refresh, logout, /auth/me)"
        Desc  = New-Desc "NLS-ADMIN-03" "Backend auth routes on admin_ui mirroring PaymentGate admin_ui/adapters/http/auth.py without AtomID exchange." @(
            "GET /api/v1/auth returns Keycloak authorize URL"
            "GET /api/v1/token exchanges code; sets split JWT cookies + refresh httponly"
            "POST /api/v1/token/refresh and POST /api/v1/logout"
            "GET /api/v1/auth/me returns UserInfo with JWT realm roles"
        ) "Supersedes NLS-GW-04 + NLS-GW-05 (Jira NLS-53, NLS-54); relates NLS-103"
    },
    @{
        Ref   = "NLS-ADMIN-04"
        Epic  = $EpicGateway
        Title = "admin_ui guard proxy to patients and ml (/guard/api/v1/*)"
        Desc  = New-Desc "NLS-ADMIN-04" "Reverse proxy from admin_ui to backend services with Keycloak Bearer forward." @(
            "Configurable service_map via settings (patients, ml, housekeeper)"
            "Reconstructs Bearer JWT from session cookies"
            "Forwards X-User-Id and correlation headers"
            "Smoke: GET /guard/api/v1/patients with session cookies"
        ) "Supersedes NLS-GW-02 (Jira NLS-51); decomposes NLS-102"
    },
    @{
        Ref   = "NLS-ADMIN-05"
        Epic  = $EpicFrontend
        Title = "React admin UI: auth pages, AuthProvider, patients MVP"
        Desc  = New-Desc "NLS-ADMIN-05" "Embedded React SPA under admin_ui/ui/: Login, Callback, AppLayout, patients list. Port patterns from PaymentGate ui/src." @(
            "/auth and /auth/callback pages with SSO button and loading states"
            "AuthService + HttpAuthBase (401 triggers refresh)"
            "ProtectedRoute gated on clinician/admin JWT roles"
            "MVP /patients page lists patients via /guard/api/v1"
        ) "Supersedes NLS-GW-07, NLS-801, NLS-802 (Jira NLS-56, NLS-47, NLS-48)"
    },
    @{
        Ref   = "NLS-ADMIN-06"
        Epic  = $EpicGateway
        Title = "admin_ui static SPA serving (frontend router + window._env_)"
        Desc  = New-Desc "NLS-ADMIN-06" "Serve built React assets from admin_ui; wildcard route returns index.html." @(
            "adapters/http/frontend.py injects runtime env into index.html"
            "npm build output copied to frontend/ in Docker image"
            "Client-side routes work on browser refresh"
        ) "PaymentGate pattern: admin_ui/adapters/http/frontend.py"
    },
    @{
        Ref   = "NLS-ADMIN-07"
        Epic  = $EpicGateway
        Title = "Docker compose: admin_ui on port 8000 (browser entry)"
        Desc  = New-Desc "NLS-ADMIN-07" "Wire admin_ui into application.compose.yml as single browser entry point." @(
            "admin_ui service on host port 8000"
            "Depends on patients and Keycloak (infra network)"
            "make up_app documents browser smoke at http://localhost:8000"
        ) "Supersedes NLS-GW-08 + NLS-GW-09 (Jira NLS-57, NLS-58)"
    },
    @{
        Ref   = "NLS-ADMIN-08"
        Epic  = $EpicPatients
        Title = "E2E smoke: browser login via admin_ui to patients API + JIT user row"
        Desc  = New-Desc "NLS-ADMIN-08" "End-to-end verification of admin_ui auth and proxied patients API." @(
            "Manual or automated: login at :8000 -> list patients -> 200"
            "patients AUTH_ENABLED=true validates forwarded Keycloak JWT"
            "JIT upsert creates users row when USER_UPSERT_ENABLED=true"
        ) "Supersedes NLS-GW-06 (Jira NLS-55); depends NLS-ADMIN-03/04/07 and NLS-17"
    },
    @{
        Ref   = "NLS-ADMIN-09"
        Epic  = $EpicIdentity
        Title = "Auth diagram: admin_ui BFF + browser OIDC flow"
        Desc  = New-Desc "NLS-ADMIN-09" "Document admin_ui browser auth flow in docs/diagrams/." @(
            "New auth-admin-ui-flow.md mermaid sequence"
            "auth-architecture.md and plan.md reference admin_ui as browser entry"
            "Note PaymentGate similarity and no AtomID exchange"
        ) "Supersedes NLS-GW-10 (Jira NLS-59)"
    }
)

Write-Output "=== admin_ui BFF + React panel tasks ==="
$Created = @()

foreach ($task in $Tasks) {
    $out = & $ApiScript create -Type Story -Summary $task.Title -Epic $task.Epic -Description $task.Desc
    $line = $out | Where-Object { $_ -match "^Created:" } | Select-Object -First 1
    if ($line -match "Created:\s+(\S+)") {
        $key = $Matches[1]
        $Created += [pscustomobject]@{ Ref = $task.Ref; JiraKey = $key; Epic = $task.Epic; Title = $task.Title }
        Write-Output ("{0} -> {1}" -f $task.Ref, $key)
    }
    else {
        throw "Failed to create $($task.Ref): $out"
    }
}

if (-not $SkipSprintAdd) {
    Write-Output ""
    Write-Output ("=== Adding $($Created.Count) stories to sprint id $SprintId ===")
    $keys = $Created | ForEach-Object { $_.JiraKey }
    & $ApiScript sprint-add $SprintId @keys
}

# Update backlog-keys.md
$mappingPath = Join-Path $RepoRoot "docs\jira\backlog-keys.md"
$append = @(
    "",
    "## admin_ui BFF + React panel (Pioneer - supersedes gateway-only browser path)",
    "",
    "| plan ref | Jira | Epic | Title |",
    "|----------|------|------|-------|"
)
foreach ($row in $Created) {
    $append += ("| {0} | {1} | {2} | {3} |" -f $row.Ref, $row.JiraKey, $row.Epic, $row.Title)
}
Add-Content -LiteralPath $mappingPath -Value ($append -join "`n") -Encoding UTF8
Write-Output "Updated docs/jira/backlog-keys.md"

Write-Output ""
Write-Output "=== Done ==="
Write-Output ("Created {0} stories; sprint {1}" -f $Created.Count, $(if ($SkipSprintAdd) { "not updated" } else { $SprintId }))
