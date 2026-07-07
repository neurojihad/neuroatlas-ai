#Requires -Version 5.1
<#
.SYNOPSIS
  Create all NeuroAtlas backlog stories from docs/jira/plan.md (skip existing Pioneer stories).
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"

# Epic Jira keys from bootstrap (plan ref -> NLS key)
$EpicKeys = @{
    "NLS-EPIC-01" = "NLS-6"
    "NLS-EPIC-02" = "NLS-7"
    "NLS-EPIC-03" = "NLS-8"
    "NLS-EPIC-04" = "NLS-9"
    "NLS-EPIC-05" = "NLS-10"
    "NLS-EPIC-06" = "NLS-11"
    "NLS-EPIC-07" = "NLS-12"
    "NLS-EPIC-08" = "NLS-13"
}

# Already created during Pioneer bootstrap (plan ref -> existing Jira key)
$Existing = @{
    "NLS-201" = "NLS-16"
    "NLS-202" = "NLS-15"
    "NLS-301" = "NLS-14"
    "NLS-302" = "NLS-17"
}

function New-StoryDescription {
    param(
        [string]$Ref,
        [string]$ArchRef,
        [string]$Status = "Open"
    )
    $partial = ""
    if ($Status -eq "Partial") {
        $partial = "`n`nStatus in repo: Partial (scaffold exists - describe remaining work in implementation)."
    }
    return (
        "## Context`n" +
        "Backlog item $Ref from docs/jira/plan.md.`n`n" +
        "## Architecture reference`n" +
        "docs/ARCHITECTURE.md $ArchRef`n`n" +
        "## Acceptance criteria`n" +
        "- [ ] Implementation matches architecture alignment in docs/ARCHITECTURE.md section 12`n" +
        "- [ ] Tests / docs updated as appropriate for this story`n`n" +
        "## Local tracker`n" +
        "docs/jira/plan.md - $Ref ($Status)$partial"
    )
}

$Stories = @(
    @{ Ref = "NLS-101"; Epic = "NLS-EPIC-01"; Title = "API Gateway service (FastAPI entry point)"; Arch = "section 12, section 5 Phase 2"; Status = "Open" },
    @{ Ref = "NLS-102"; Epic = "NLS-EPIC-01"; Title = "Gateway routing to patients / ml / housekeeper"; Arch = "section 4 Gateway"; Status = "Open" },
    @{ Ref = "NLS-103"; Epic = "NLS-EPIC-01"; Title = "Centralize OIDC auth at gateway"; Arch = "section 5 Phase 2"; Status = "Open" },
    @{ Ref = "NLS-104"; Epic = "NLS-EPIC-01"; Title = "Rate limiting at gateway (Redis-backed)"; Arch = "section 4 Gateway, section 6 Redis"; Status = "Open" },
    @{ Ref = "NLS-105"; Epic = "NLS-EPIC-01"; Title = "Per-service Docker deploy targets in CI"; Arch = "section 12"; Status = "Open" },
    @{ Ref = "NLS-106"; Epic = "NLS-EPIC-01"; Title = "Database-per-service strategy (design + ADR)"; Arch = "section 12"; Status = "Open" },

    @{ Ref = "NLS-203"; Epic = "NLS-EPIC-02"; Title = "Patients service integration tests against Postgres"; Arch = "section 12"; Status = "Open" },
    @{ Ref = "NLS-204"; Epic = "NLS-EPIC-02"; Title = "Patient-level ACL (auth Phase 4)"; Arch = "section 5 Phase 4"; Status = "Open" },

    @{ Ref = "NLS-303"; Epic = "NLS-EPIC-03"; Title = "Audit events table + correlation with user_id"; Arch = "section 5"; Status = "Open" },
    @{ Ref = "NLS-304"; Epic = "NLS-EPIC-03"; Title = "Service accounts (client credentials) for ML"; Arch = "section 5 Phase 3"; Status = "Open" },

    @{ Ref = "NLS-401"; Epic = "NLS-EPIC-04"; Title = "Kafka topic bootstrap automation in CI"; Arch = "section 7"; Status = "Partial" },
    @{ Ref = "NLS-402"; Epic = "NLS-EPIC-04"; Title = "Transactional outbox pattern in common/"; Arch = "section 12"; Status = "Open" },
    @{ Ref = "NLS-403"; Epic = "NLS-EPIC-04"; Title = "Saga design for prediction-requested flow"; Arch = "section 7, section 12"; Status = "Open" },
    @{ Ref = "NLS-404"; Epic = "NLS-EPIC-04"; Title = "Dead-letter / retry policy for consumers"; Arch = "section 12"; Status = "Open" },

    @{ Ref = "NLS-501"; Epic = "NLS-EPIC-05"; Title = "Ingestion service - PubMed import"; Arch = "section 4 Ingestion, section 10 Phase 2"; Status = "Open" },
    @{ Ref = "NLS-502"; Epic = "NLS-EPIC-05"; Title = "Article storage schema + chunking"; Arch = "section 10 Phase 2"; Status = "Open" },
    @{ Ref = "NLS-503"; Epic = "NLS-EPIC-05"; Title = "Embedding service - vector generation"; Arch = "section 4 Embedding, section 10 Phase 3"; Status = "Open" },
    @{ Ref = "NLS-504"; Epic = "NLS-EPIC-05"; Title = "Search service - pgvector semantic retrieval"; Arch = "section 4 Search, section 10 Phase 4"; Status = "Open" },
    @{ Ref = "NLS-505"; Epic = "NLS-EPIC-05"; Title = "LLM Orchestrator - RAG + citations"; Arch = "section 4, section 10 Phase 4"; Status = "Open" },
    @{ Ref = "NLS-506"; Epic = "NLS-EPIC-05"; Title = "Redis cache for search / LLM responses"; Arch = "section 6 Redis"; Status = "Open" },

    @{ Ref = "NLS-601"; Epic = "NLS-EPIC-06"; Title = "ML Kafka consumer hardening (prod config)"; Arch = "section 4 ML"; Status = "Partial" },
    @{ Ref = "NLS-602"; Epic = "NLS-EPIC-06"; Title = "XGBoost production predictor adapter"; Arch = "section 4 ML, section 10 Phase 6"; Status = "Open" },
    @{ Ref = "NLS-603"; Epic = "NLS-EPIC-06"; Title = "SHAP explainability endpoint"; Arch = "section 4 ML"; Status = "Open" },
    @{ Ref = "NLS-604"; Epic = "NLS-EPIC-06"; Title = "Clinical feature store schema"; Arch = "section 3"; Status = "Open" },

    @{ Ref = "NLS-701"; Epic = "NLS-EPIC-07"; Title = "Prometheus /metrics on all services"; Arch = "section 12"; Status = "Open" },
    @{ Ref = "NLS-702"; Epic = "NLS-EPIC-07"; Title = "Distributed tracing (OpenTelemetry)"; Arch = "section 12"; Status = "Open" },
    @{ Ref = "NLS-703"; Epic = "NLS-EPIC-07"; Title = "Housekeeper long-query monitoring (Postgres)"; Arch = "section 4 Housekeeper"; Status = "Partial" },
    @{ Ref = "NLS-704"; Epic = "NLS-EPIC-07"; Title = "Structured audit log export"; Arch = "section 12"; Status = "Open" },

    @{ Ref = "NLS-801"; Epic = "NLS-EPIC-08"; Title = "Next.js app scaffold"; Arch = "section 10 Phase 5"; Status = "Open" },
    @{ Ref = "NLS-802"; Epic = "NLS-EPIC-08"; Title = "Keycloak login flow in UI"; Arch = "section 5"; Status = "Open" },
    @{ Ref = "NLS-803"; Epic = "NLS-EPIC-08"; Title = "Gateway integration from UI"; Arch = "section 10 Phase 5"; Status = "Open" }
)

Write-Output "=== NeuroAtlas backlog bootstrap ==="
Write-Output "Creating stories on backlog only (no sprint assignment)."
Write-Output ""

$Created = @()
$Skipped = @()

foreach ($story in $Stories) {
    if ($Existing.ContainsKey($story.Ref)) {
        $Skipped += [pscustomobject]@{ Ref = $story.Ref; JiraKey = $Existing[$story.Ref]; Reason = "already exists" }
        Write-Output ("SKIP {0} -> {1}" -f $story.Ref, $Existing[$story.Ref])
        continue
    }

    $epicKey = $EpicKeys[$story.Epic]
    $desc = New-StoryDescription -Ref $story.Ref -ArchRef $story.Arch -Status $story.Status
    $out = & $ApiScript create -Type Story -Summary $story.Title -Epic $epicKey -Description $desc
    $line = ($out | Where-Object { $_ -match "^Created:" } | Select-Object -First 1)
    if ($line -match "Created:\s+(\S+)") {
        $key = $Matches[1]
        $Created += [pscustomobject]@{ Ref = $story.Ref; JiraKey = $key; Epic = $story.Epic; Title = $story.Title }
        Write-Output ("CREATE {0} -> {1} (epic {2})" -f $story.Ref, $key, $epicKey)
    }
    else {
        throw "Failed to create $($story.Ref): $out"
    }
}

Write-Output ""
Write-Output "=== Summary ==="
Write-Output ("Created: {0}" -f $Created.Count)
Write-Output ("Skipped: {0}" -f $Skipped.Count)
Write-Output ""
Write-Output "--- Key mapping (new) ---"
foreach ($row in $Created) {
    Write-Output ("{0} -> {1}" -f $row.Ref, $row.JiraKey)
}

# Write mapping file for docs
$mappingPath = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "docs\jira\backlog-keys.md"
$lines = @(
    "# NeuroAtlas - Jira backlog key mapping",
    "",
    "Project key: **NLS**. Plan refs (`NLS-*`) map to auto-assigned Jira keys.",
    "",
    "## Epics",
    "",
    "| plan.md | Jira | Title |",
    "|---------|------|-------|",
    "| NLS-EPIC-01 | NLS-6 | Microservice foundation |",
    "| NLS-EPIC-02 | NLS-7 | Clinical data (Patients) |",
    "| NLS-EPIC-03 | NLS-8 | Identity & audit |",
    "| NLS-EPIC-04 | NLS-9 | Event backbone |",
    "| NLS-EPIC-05 | NLS-10 | Knowledge base (RAG pipeline) |",
    "| NLS-EPIC-06 | NLS-11 | Machine learning |",
    "| NLS-EPIC-07 | NLS-12 | Observability & ops |",
    "| NLS-EPIC-08 | NLS-13 | Frontend |",
    "",
    "## Stories",
    "",
    "| plan.md | Jira | Epic | Title |",
    "|---------|------|------|-------|"
)

$allStories = @(
    @{ Ref = "NLS-101"; Epic = "EPIC-01"; Title = "API Gateway service (FastAPI entry point)"; Key = "" },
    @{ Ref = "NLS-102"; Epic = "EPIC-01"; Title = "Gateway routing to patients / ml / housekeeper"; Key = "" },
    @{ Ref = "NLS-103"; Epic = "EPIC-01"; Title = "Centralize OIDC auth at gateway"; Key = "" },
    @{ Ref = "NLS-104"; Epic = "EPIC-01"; Title = "Rate limiting at gateway (Redis-backed)"; Key = "" },
    @{ Ref = "NLS-105"; Epic = "EPIC-01"; Title = "Per-service Docker deploy targets in CI"; Key = "" },
    @{ Ref = "NLS-106"; Epic = "EPIC-01"; Title = "Database-per-service strategy (design + ADR)"; Key = "" },
    @{ Ref = "NLS-201"; Epic = "EPIC-02"; Title = "Patients SQLAlchemy adapter"; Key = "NLS-16" },
    @{ Ref = "NLS-202"; Epic = "EPIC-02"; Title = "Alembic migrations"; Key = "NLS-15" },
    @{ Ref = "NLS-203"; Epic = "EPIC-02"; Title = "Patients integration tests against Postgres"; Key = "" },
    @{ Ref = "NLS-204"; Epic = "EPIC-02"; Title = "Patient-level ACL"; Key = "" },
    @{ Ref = "NLS-301"; Epic = "EPIC-03"; Title = "Keycloak realm bootstrap"; Key = "NLS-14" },
    @{ Ref = "NLS-302"; Epic = "EPIC-03"; Title = "JIT user upsert"; Key = "NLS-17" },
    @{ Ref = "NLS-303"; Epic = "EPIC-03"; Title = "Audit events table"; Key = "" },
    @{ Ref = "NLS-304"; Epic = "EPIC-03"; Title = "Service accounts for ML"; Key = "" },
    @{ Ref = "NLS-401"; Epic = "EPIC-04"; Title = "Kafka topic bootstrap in CI"; Key = "" },
    @{ Ref = "NLS-402"; Epic = "EPIC-04"; Title = "Transactional outbox"; Key = "" },
    @{ Ref = "NLS-403"; Epic = "EPIC-04"; Title = "Saga design"; Key = "" },
    @{ Ref = "NLS-404"; Epic = "EPIC-04"; Title = "Dead-letter / retry policy"; Key = "" },
    @{ Ref = "NLS-501"; Epic = "EPIC-05"; Title = "PubMed ingestion"; Key = "" },
    @{ Ref = "NLS-502"; Epic = "EPIC-05"; Title = "Article storage + chunking"; Key = "" },
    @{ Ref = "NLS-503"; Epic = "EPIC-05"; Title = "Embedding service"; Key = "" },
    @{ Ref = "NLS-504"; Epic = "EPIC-05"; Title = "Search service (pgvector)"; Key = "" },
    @{ Ref = "NLS-505"; Epic = "EPIC-05"; Title = "LLM Orchestrator RAG"; Key = "" },
    @{ Ref = "NLS-506"; Epic = "EPIC-05"; Title = "Redis cache search/LLM"; Key = "" },
    @{ Ref = "NLS-601"; Epic = "EPIC-06"; Title = "ML Kafka consumer hardening"; Key = "" },
    @{ Ref = "NLS-602"; Epic = "EPIC-06"; Title = "XGBoost production adapter"; Key = "" },
    @{ Ref = "NLS-603"; Epic = "EPIC-06"; Title = "SHAP explainability"; Key = "" },
    @{ Ref = "NLS-604"; Epic = "EPIC-06"; Title = "Clinical feature store schema"; Key = "" },
    @{ Ref = "NLS-701"; Epic = "EPIC-07"; Title = "Prometheus metrics"; Key = "" },
    @{ Ref = "NLS-702"; Epic = "EPIC-07"; Title = "OpenTelemetry tracing"; Key = "" },
    @{ Ref = "NLS-703"; Epic = "EPIC-07"; Title = "Housekeeper long-query monitoring"; Key = "" },
    @{ Ref = "NLS-704"; Epic = "EPIC-07"; Title = "Structured audit log export"; Key = "" },
    @{ Ref = "NLS-801"; Epic = "EPIC-08"; Title = "Next.js scaffold"; Key = "" },
    @{ Ref = "NLS-802"; Epic = "EPIC-08"; Title = "Keycloak login UI"; Key = "" },
    @{ Ref = "NLS-803"; Epic = "EPIC-08"; Title = "Gateway UI integration"; Key = "" }
)

foreach ($row in $Created) {
    $match = $allStories | Where-Object { $_.Ref -eq $row.Ref } | Select-Object -First 1
    if ($match) { $match.Key = $row.JiraKey }
}

foreach ($s in $allStories) {
    if (-not $s.Key) {
        $skip = $Skipped | Where-Object { $_.Ref -eq $s.Ref } | Select-Object -First 1
        if ($skip) { $s.Key = $skip.JiraKey }
    }
    if ($s.Key) {
        $lines += ("| {0} | {1} | {2} | {3} |" -f $s.Ref, $s.Key, $s.Epic, $s.Title)
    }
}

Set-Content -LiteralPath $mappingPath -Value ($lines -join "`n") -Encoding UTF8
Write-Output ""
Write-Output ("Mapping written to docs/jira/backlog-keys.md")
