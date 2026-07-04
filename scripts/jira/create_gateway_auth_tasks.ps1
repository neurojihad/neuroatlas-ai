#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"

$EpicGateway = "NLS-6"
$EpicIdentity = "NLS-8"
$EpicPatients = "NLS-7"
$EpicFrontend = "NLS-13"

function New-Desc {
    param([string]$Ref, [string]$Context, [string[]]$AC, [string]$Refs = "", [string]$Arch = "docs/ARCHITECTURE.md section 5, docs/diagrams/auth-architecture.md")
    $acLines = ($AC | ForEach-Object { "- [ ] $_" }) -join "`n"
    $related = ""
    if ($Refs) { $related = "`n## Related backlog`n$Refs`n" }
    return @"
## Context
$Context

Sprint: Pioneer (gateway + browser Keycloak auth). Tracker ref: $Ref

## Architecture reference
$Arch

## Acceptance criteria
$acLines
$related
## Docs
- docs/diagrams/auth-request-flow.md
- docs/diagrams/auth-keycloak-user-registration.md
- docs/jira/sprint-01-pioneer.md
"@
}

$Tasks = @(
    @{
        Ref  = "NLS-GW-01"
        Epic = $EpicGateway
        Title = "Gateway service scaffold (embed pattern, src/gateway/)"
        Desc = New-Desc "NLS-GW-01" "Hexagonal FastAPI gateway module: main, lifespan, settings, health. First step toward embedded gateway (see existing NLS-18)." @(
            "src/gateway/ follows patients/ml service layout"
            "make run_gateway or compose target documented"
            "Health endpoint returns 200"
        ) "Decomposes plan NLS-101; relates to Jira NLS-18, NLS-19"
    },
    @{
        Ref  = "NLS-GW-02"
        Epic = $EpicGateway
        Title = "Gateway reverse proxy to patients, ml, housekeeper"
        Desc = New-Desc "NLS-GW-02" "HTTP reverse proxy routes /api/patients, /api/ml, /api/hk to backend services." @(
            "Configurable upstream URLs via env"
            "Preserves path and query string"
            "Smoke: GET patients /health via gateway"
        ) "Decomposes plan NLS-102; relates to Jira NLS-20"
    },
    @{
        Ref  = "NLS-GW-03"
        Epic = $EpicIdentity
        Title = "Keycloak browser client: redirect URIs, CORS, neuroatlas-ui"
        Desc = New-Desc "NLS-GW-03" "Configure Keycloak client for browser authorization code flow (local + Docker)." @(
            "Public or confidential SPA client with PKCE documented"
            "Redirect URIs for localhost frontend and gateway callback"
            "CORS origins for local dev in realm or client"
            "Updated in infra/keycloak/import/neuroatlas-realm.json"
        ) "Extends NLS-14 (NLS-301); prerequisite for browser login"
    },
    @{
        Ref  = "NLS-GW-04"
        Epic = $EpicGateway
        Title = "Gateway OIDC routes: login, callback, logout (browser)"
        Desc = New-Desc "NLS-GW-04" "Browser-facing OIDC at gateway: redirect to Keycloak, handle callback, logout." @(
            "/auth/login redirects to Keycloak authorize endpoint"
            "/auth/callback exchanges code for tokens (PKCE)"
            "/auth/logout clears session and Keycloak SSO"
            "Errors logged with structlog; no secrets in logs"
        ) "Auth Phase 2 browser path; relates to NLS-21"
    },
    @{
        Ref  = "NLS-GW-05"
        Epic = $EpicGateway
        Title = "Gateway session cookie and Bearer forwarding to backends"
        Desc = New-Desc "NLS-GW-05" "After browser login, gateway holds session and forwards JWT to backend services." @(
            "HttpOnly secure cookie or server-side session stores tokens"
            "Proxy injects Authorization Bearer on upstream requests"
            "Token refresh before expiry where applicable"
            "AUTH_ENABLED=true path documented for local smoke"
        ) "Centralizes OIDC at gateway; relates to NLS-21, NLS-103"
    },
    @{
        Ref  = "NLS-GW-06"
        Epic = $EpicPatients
        Title = "Patients API auth smoke via gateway with real Keycloak JWT"
        Desc = New-Desc "NLS-GW-06" "Verify patients service accepts tokens obtained through browser+gateway path." @(
            "Manual or automated smoke: login -> gateway -> GET /api/v1/patients"
            "require_clinician returns 401 without token, 200 with clinician role"
            "JIT upsert runs when USER_UPSERT_ENABLED=true"
        ) "Depends NLS-GW-04/05 and NLS-14/17; relates to NLS-302"
    },
    @{
        Ref  = "NLS-GW-07"
        Epic = $EpicFrontend
        Title = "Frontend Keycloak browser login (OIDC redirect / PKCE)"
        Desc = New-Desc "NLS-GW-07" "Minimal UI login flow calling gateway or Keycloak directly for browser users." @(
            "Login button triggers OIDC redirect"
            "Callback page handles token or delegates to gateway session"
            "Displays authenticated user email/roles (dev only)"
        ) "Decomposes plan NLS-802; relates to Jira NLS-48"
    },
    @{
        Ref  = "NLS-GW-08"
        Epic = $EpicFrontend
        Title = "Frontend API integration through gateway entry point"
        Desc = New-Desc "NLS-GW-08" "All browser API calls go through gateway base URL, not direct service ports." @(
            "Env var GATEWAY_URL / NEXT_PUBLIC_API_URL"
            "Authenticated fetch includes session cookie or Bearer"
            "CORS works for local Next.js + gateway"
        ) "Decomposes plan NLS-803; relates to Jira NLS-49"
    },
    @{
        Ref  = "NLS-GW-09"
        Epic = $EpicGateway
        Title = "Docker compose: gateway service on application stack"
        Desc = New-Desc "NLS-GW-09" "Wire gateway into infra/application compose with Keycloak and backends." @(
            "application.compose.yml includes gateway on port 8000"
            "make up_app starts gateway with patients/ml/hk upstreams"
            "README documents browser auth smoke path"
        ) "Infra for Pioneer gateway slice"
    },
    @{
        Ref  = "NLS-GW-10"
        Epic = $EpicIdentity
        Title = "Auth diagram: gateway + browser OIDC flow"
        Desc = New-Desc "NLS-GW-10" "Document end-to-end browser auth through gateway in docs/diagrams/." @(
            "New or updated mermaid: browser -> Keycloak -> gateway -> patients"
            "Linked from auth-architecture.md and ARCHITECTURE.md section 5"
        ) "" "docs/diagrams/"
    }
)

Write-Output "=== Gateway + browser auth tasks (backlog only) ==="
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
        throw "Failed: $($task.Ref)"
    }
}

Write-Output ""
Write-Output "Created $($Created.Count) stories. Add to Pioneer sprint manually in Jira."

# Append to backlog-keys.md
$mappingPath = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "docs\jira\backlog-keys.md"
$append = @("", "## Gateway + browser auth (Pioneer extension)", "", "| plan ref | Jira | Epic | Title |", "|----------|------|------|-------|")
foreach ($row in $Created) {
    $append += ("| {0} | {1} | {2} | {3} |" -f $row.Ref, $row.JiraKey, $row.Epic, $row.Title)
}
Add-Content -LiteralPath $mappingPath -Value ($append -join "`n") -Encoding UTF8
Write-Output "Updated docs/jira/backlog-keys.md"
