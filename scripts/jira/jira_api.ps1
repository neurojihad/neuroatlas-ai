#Requires -Version 5.1
<#
.SYNOPSIS
  Thin wrapper around the Atlassian Cloud REST API for NeuroAtlas Jira ops.

.DESCRIPTION
  Loads JIRA_* variables from infra/.env. Requires JIRA_EMAIL and JIRA_API_TOKEN.

.EXAMPLE
  .\scripts\jira\jira_api.ps1 search "project = NLS AND status != Done"
  .\scripts\jira\jira_api.ps1 get NLS-201
  .\scripts\jira\jira_api.ps1 create -Type Story -Summary "Patients SQLAlchemy adapter" -Epic NLS-EPIC-02 -Description "See ARCHITECTURE.md section 12"
#>
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Arg1,

    [string]$Type = "Story",
    [string]$Summary,
    [string]$Epic,
    [string]$Description,
    [string]$DescriptionFile,
    [int]$BoardId = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $dir = Split-Path -Parent $PSScriptRoot
    Split-Path -Parent $dir
}

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) {
            return
        }
        if ($line -match '^\s*([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

function Get-JiraConfig {
    $root = Get-RepoRoot
    Import-DotEnv (Join-Path $root "infra\.env")

    $baseUrl = if ($env:JIRA_BASE_URL) { $env:JIRA_BASE_URL.TrimEnd("/") } else { "https://neurojihad.atlassian.net" }
    $email = $env:JIRA_EMAIL
    $token = $env:JIRA_API_TOKEN
    $project = if ($env:JIRA_PROJECT_KEY) { $env:JIRA_PROJECT_KEY } else { "NLS" }

    if (-not $email -or -not $token) {
        throw "Set JIRA_EMAIL and JIRA_API_TOKEN in infra/.env (see infra/.env.example)."
    }

    $pair = "{0}:{1}" -f $email, $token
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($pair)
    $auth = [Convert]::ToBase64String($bytes)

    return @{
        BaseUrl = $baseUrl
        Auth    = $auth
        Project = $project
    }
}

function Escape-JsonString {
    param([string]$Value)
    if (-not $Value) { return "" }
    return ($Value -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '' -replace "`n", '\n' -replace "`t", '\t')
}

function ConvertTo-AdfJsonString {
    param([string]$Text)
    if (-not $Text) { $Text = "" }
    $lines = $Text -split "`r?`n"
    $paragraphs = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) {
        if ($line -eq "") { continue }
        $escaped = Escape-JsonString -Value $line
        $paragraphs.Add("{""type"":""paragraph"",""content"":[{""type"":""text"",""text"":""$escaped""}]}")
    }
    if ($paragraphs.Count -eq 0) {
        $paragraphs.Add("{""type"":""paragraph"",""content"":[{""type"":""text"",""text"":""""}]}")
    }
    $content = $paragraphs -join ","
    return "{""type"":""doc"",""version"":1,""content"":[$content]}"
}

function ConvertTo-CreateIssueJson {
    param(
        [string]$Project,
        [string]$Summary,
        [string]$Type,
        [string]$DescriptionText,
        [string]$EpicKey = ""
    )
    $adf = ConvertTo-AdfJsonString -Text $DescriptionText
    $summaryEscaped = Escape-JsonString -Value $Summary
    $json = "{""fields"":{""project"":{""key"":""$Project""},""summary"":""$summaryEscaped"",""description"":$adf,""issuetype"":{""name"":""$Type""}"
    if ($EpicKey) {
        $json += ",""parent"":{""key"":""$EpicKey""}"
    }
    $json += "}}"
    return $json
}

function ConvertTo-AdfDocument {
    param([string]$Text)
    if (-not $Text) {
        $Text = ""
    }
    $paragraphs = $Text -split "`r?`n"
    $content = @()
    foreach ($para in $paragraphs) {
        if ($para -eq "") {
            continue
        }
        $content += @{
            type    = "paragraph"
            content = @(
                @{
                    type = "text"
                    text = $para
                }
            )
        }
    }
    if ($content.Count -eq 0) {
        $content = @(
            @{
                type    = "paragraph"
                content = @(@{ type = "text"; text = "" })
            }
        )
    }
    return @{
        type    = "doc"
        version = 1
        content = $content
    }
}

function Invoke-JiraRequest {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [string]$BodyJson = ""
    )
    $cfg = Get-JiraConfig
    $uri = "{0}{1}" -f $cfg.BaseUrl, $Path
    $headers = @{
        Authorization = "Basic {0}" -f $cfg.Auth
        Accept        = "application/json"
    }
    $params = @{
        Method  = $Method
        Uri     = $uri
        Headers = $headers
    }
    if ($BodyJson) {
        $params["Body"] = $BodyJson
        $params["ContentType"] = "application/json; charset=utf-8"
    }
    elseif ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 20 -Compress
        $params["Body"] = $json
        $params["ContentType"] = "application/json; charset=utf-8"
    }
    try {
        return Invoke-RestMethod @params
    }
    catch {
        $detail = $_.ToString()
        if ($null -ne $_.Exception -and $null -ne $_.Exception.Message) {
            $detail = $_.Exception.Message
        }
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            $detail = $_.ErrorDetails.Message
        }
        if ($null -ne $_.Exception -and $null -ne $_.Exception.Response) {
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                if ($null -ne $stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $responseBody = $reader.ReadToEnd()
                    if ($responseBody) {
                        $detail = $responseBody
                    }
                }
            }
            catch {
                # keep prior detail
            }
        }
        throw "Jira API $Method $Path failed: $detail"
    }
}

function Get-DescriptionText {
    if ($DescriptionFile) {
        if (-not (Test-Path -LiteralPath $DescriptionFile)) {
            throw "Description file not found: $DescriptionFile"
        }
        return Get-Content -LiteralPath $DescriptionFile -Raw
    }
    return $Description
}

$cfg = Get-JiraConfig

switch ($Command.ToLowerInvariant()) {
    "search" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 search ""project = NLS AND status != Done"""
        }
        $body = @{
            jql        = $Arg1
            maxResults = 50
            fields     = @("summary", "status", "issuetype", "parent")
        }
        $result = Invoke-JiraRequest -Method POST -Path "/rest/api/3/search/jql" -Body $body
        $result.issues | ForEach-Object {
            $key = $_.key
            $summary = $_.fields.summary
            $status = $_.fields.status.name
            Write-Output ("{0}  [{1}]  {2}" -f $key, $status, $summary)
        }
        if (-not $result.issues -or $result.issues.Count -eq 0) {
            Write-Output "(no issues)"
        }
    }

    "get" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 get NLS-201"
        }
        $issue = Invoke-JiraRequest -Method GET -Path ("/rest/api/3/issue/{0}?fields=summary,status,description,issuetype,parent" -f $Arg1)
        Write-Output ("Key:     {0}" -f $issue.key)
        Write-Output ("Summary: {0}" -f $issue.fields.summary)
        Write-Output ("Status:  {0}" -f $issue.fields.status.name)
        Write-Output ("Type:    {0}" -f $issue.fields.issuetype.name)
    }

    "create" {
        if (-not $Summary) {
            throw "Usage: jira_api.ps1 create -Type Story -Summary ""..."" [-Epic NLS-EPIC-02] [-Description ""..."" | -DescriptionFile path]"
        }
        $descText = Get-DescriptionText
        $json = ConvertTo-CreateIssueJson -Project $cfg.Project -Summary $Summary -Type $Type -DescriptionText $descText -EpicKey $Epic
        $result = Invoke-JiraRequest -Method POST -Path "/rest/api/3/issue" -BodyJson $json
        Write-Output ("Created: {0}" -f $result.key)
        Write-Output ("URL:     {0}/browse/{1}" -f $cfg.BaseUrl, $result.key)
    }

    "transitions" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 transitions NLS-201"
        }
        $result = Invoke-JiraRequest -Method GET -Path ("/rest/api/3/issue/{0}/transitions" -f $Arg1)
        $result.transitions | ForEach-Object {
            Write-Output ("{0}: {1}" -f $_.id, $_.name)
        }
    }

    "comment" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 comment NLS-201 -Description ""..."" "
        }
        $descText = Get-DescriptionText
        if (-not $descText) {
            throw "Provide -Description or -DescriptionFile for comment text."
        }
        $body = @{
            body = ConvertTo-AdfDocument -Text $descText
        }
        Invoke-JiraRequest -Method POST -Path ("/rest/api/3/issue/{0}/comment" -f $Arg1) -Body $body | Out-Null
        Write-Output ("Comment added to {0}" -f $Arg1)
    }

    "boards" {
        $result = Invoke-JiraRequest -Method GET -Path "/rest/agile/1.0/board?projectKeyOrId=$($cfg.Project)"
        $result.values | ForEach-Object {
            Write-Output ("{0}: {1}" -f $_.id, $_.name)
        }
    }

    "projects" {
        $result = Invoke-JiraRequest -Method GET -Path "/rest/api/3/project/search?maxResults=50"
        $result.values | ForEach-Object {
            Write-Output ("{0}: {1}" -f $_.key, $_.name)
        }
        if (-not $result.values -or $result.values.Count -eq 0) {
            Write-Output "(no projects)"
        }
    }

    "verify" {
        $me = Invoke-JiraRequest -Method GET -Path "/rest/api/3/myself"
        Write-Output ("OK: {0} ({1})" -f $me.displayName, $me.emailAddress)
        try {
            $project = Invoke-JiraRequest -Method GET -Path "/rest/api/3/project/$($cfg.Project)"
            Write-Output ("Project: {0} - {1}" -f $project.key, $project.name)
        }
        catch {
            Write-Output ("Project $($cfg.Project): not found - create it in Jira or fix JIRA_PROJECT_KEY")
        }
    }

    "sprints" {
        if ($BoardId -eq 0) {
            throw "Usage: jira_api.ps1 sprints -BoardId <id>   (run 'boards' first)"
        }
        $result = Invoke-JiraRequest -Method GET -Path ("/rest/agile/1.0/board/{0}/sprint" -f $BoardId)
        $result.values | ForEach-Object {
            Write-Output ("{0}: {1} [{2}]" -f $_.id, $_.name, $_.state)
        }
    }

    "sprint-issues" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 sprint-issues <sprint_id>"
        }
        $result = Invoke-JiraRequest -Method GET -Path ("/rest/agile/1.0/sprint/{0}/issue?maxResults=50" -f $Arg1)
        if (-not $result.issues -or $result.issues.Count -eq 0) {
            Write-Output "(no issues)"
        }
        else {
            $result.issues | ForEach-Object {
                Write-Output $_.key
            }
        }
    }

    "start-sprint" {
        if (-not $Arg1) {
            throw "Usage: jira_api.ps1 start-sprint <sprint_id>"
        }
        $current = Invoke-JiraRequest -Method GET -Path ("/rest/agile/1.0/sprint/{0}" -f $Arg1)
        $start = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $end = (Get-Date).AddDays(14).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $body = @{
            name      = $current.name
            state     = "active"
            startDate = $start
            endDate   = $end
        }
        if ($current.goal) {
            $body["goal"] = $current.goal
        }
        $result = Invoke-JiraRequest -Method PUT -Path ("/rest/agile/1.0/sprint/{0}" -f $Arg1) -Body $body
        Write-Output ("Started: {0} (id {1}) [{2}]" -f $result.name, $result.id, $result.state)
    }

    default {
        throw "Unknown command '$Command'. Use: search, get, create, transitions, comment, boards, projects, verify, sprints, sprint-issues, start-sprint"
    }
}
