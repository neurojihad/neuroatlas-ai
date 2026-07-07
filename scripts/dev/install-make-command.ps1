# Install `make` for Windows PowerShell (profile function + venv PATH shim).
# Run once from repo root:  .\scripts\dev\install-make-command.ps1

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$markerStart = "# >>> neuroatlas-make >>>"
$markerEnd = "# <<< neuroatlas-make <<<"

$makeFunction = @"
$markerStart
function make {
    `$dir = `$PWD.Path
    while (`$dir) {
        `$shim = Join-Path `$dir "make.cmd"
        if (Test-Path `$shim) {
            & `$shim @args
            return `$LASTEXITCODE
        }
        `$parent = Split-Path `$dir -Parent
        if (-not `$parent -or `$parent -eq `$dir) { break }
        `$dir = `$parent
    }
    Write-Error "make.cmd not found. cd to the NeuroAtlas repo root or use .\make.cmd <target>."
}
$markerEnd
"@

function Install-MakeProfile {
    param([string]$ProfilePath)

    if (-not $ProfilePath) {
        return
    }

    $profileDir = Split-Path $ProfilePath -Parent
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }

    if (Test-Path $ProfilePath) {
        $existing = Get-Content $ProfilePath -Raw
        if ($existing -match [regex]::Escape($markerStart)) {
            $pattern = "(?s)$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))"
            $updated = [regex]::Replace($existing, $pattern, $makeFunction.TrimEnd())
        }
        else {
            $updated = $existing.TrimEnd() + "`n`n" + $makeFunction
        }
    }
    else {
        $updated = $makeFunction
    }

    Set-Content -Path $ProfilePath -Value $updated -Encoding UTF8
    Write-Host "  profile: $ProfilePath" -ForegroundColor Green
}

Write-Host "Installing NeuroAtlas make command..." -ForegroundColor Cyan

$profilePaths = @(
    $PROFILE.CurrentUserAllHosts,
    (Join-Path $HOME "Documents\PowerShell\profile.ps1"),
    (Join-Path $HOME "Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1")
) | Select-Object -Unique

foreach ($path in $profilePaths) {
    Install-MakeProfile -ProfilePath $path
}

& (Join-Path $PSScriptRoot "install-venv-make.ps1")

Write-Host ""
Write-Host "Done. With (.venv) active you can run:" -ForegroundColor Cyan
Write-Host "  make fmt"
Write-Host "  make lint"
Write-Host ""
Write-Host "If make still fails, run once: .\make.cmd setup_make  (PyCharm: then open a NEW terminal tab)"
