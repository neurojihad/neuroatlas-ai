#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Get-Content (Join-Path $root "infra\.env") | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    if ($line -match '^\s*([^=]+)=(.*)$') {
        Set-Item -Path ("env:{0}" -f $matches[1].Trim()) -Value $matches[2].Trim()
    }
}

$oldKey = $env:JIRA_PROJECT_KEY
if (-not $oldKey) { $oldKey = "SCRUM" }
$newKey = "NLS"

if ($oldKey -eq $newKey) {
    Write-Output "Project key already $newKey"
    exit 0
}

$auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(("{0}:{1}" -f $env:JIRA_EMAIL, $env:JIRA_API_TOKEN)))
$h = @{ Authorization = "Basic $auth"; Accept = "application/json" }
$base = $env:JIRA_BASE_URL.TrimEnd("/")

Write-Output "Renaming Jira project key: $oldKey -> $newKey"

$project = Invoke-RestMethod -Uri "$base/rest/api/3/project/$oldKey" -Headers $h
$body = @{
    key  = $newKey
    name = $project.name
} | ConvertTo-Json -Compress

$result = Invoke-RestMethod -Method PUT -Uri "$base/rest/api/3/project/$oldKey" -Headers $h -ContentType "application/json" -Body $body
Write-Output ("Project renamed: {0} - {1}" -f $result.key, $result.name)
Write-Output "All issue keys $oldKey-* are now $newKey-* (old keys redirect in Jira)."

# Update infra/.env
$envPath = Join-Path $root "infra\.env"
$content = Get-Content -LiteralPath $envPath -Raw
$content = $content -replace "JIRA_PROJECT_KEY=$oldKey", "JIRA_PROJECT_KEY=$newKey"
Set-Content -LiteralPath $envPath -Value $content -NoNewline -Encoding UTF8
Write-Output "Updated infra/.env JIRA_PROJECT_KEY=$newKey"
