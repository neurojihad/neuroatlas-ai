# Install `make` for Windows / PyCharm.
#   .\make.cmd setup_make

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$binDir = Join-Path $repoRoot "bin"

$markerStart = "# >>> neuroatlas-make >>>"
$markerEnd = "# <<< neuroatlas-make <<<"

function Test-RealPython {
    param([string]$PythonExe)

    if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
        return $false
    }
    if ($PythonExe -match "WindowsApps|Microsoft\\WindowsApps") {
        return $false
    }

    $output = & $PythonExe -V 2>&1
    return ($LASTEXITCODE -eq 0 -and "$output" -match "^Python 3\.")
}

function Get-PythonCandidates {
    $paths = @()

    if (Get-Command where.exe -ErrorAction SilentlyContinue) {
        $paths += (& where.exe python 2>$null) -split "`r?`n"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $paths += Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $resolved = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($resolved) {
            $paths += $resolved.Trim()
        }
    }

    return $paths | Where-Object { $_ } | Select-Object -Unique
}

function Get-ScriptsFromPython {
    param([string]$PythonExe)

    if (-not (Test-RealPython $PythonExe)) {
        return $null
    }

    $scriptsDir = Split-Path $PythonExe -Parent
    if ((Split-Path $scriptsDir -Leaf) -ieq "Scripts") {
        return $scriptsDir
    }

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $prefixScripts = (& $PythonExe -c "import os, sys; print(os.path.join(sys.prefix, 'Scripts'))" 2>$null).Trim()
        if ($prefixScripts -and (Test-Path $prefixScripts)) {
            return $prefixScripts
        }
    }
    finally {
        $ErrorActionPreference = $oldEap
    }

    return $null
}

function Get-VenvScriptsPath {
    foreach ($pythonExe in Get-PythonCandidates) {
        $scripts = Get-ScriptsFromPython -PythonExe $pythonExe
        if ($scripts) {
            return $scripts
        }
    }

    if ($env:VIRTUAL_ENV) {
        $scripts = Join-Path $env:VIRTUAL_ENV "Scripts"
        if (Test-Path $scripts) {
            return $scripts
        }
    }

    foreach ($name in @(".venv", "venv")) {
        $scripts = Join-Path $repoRoot "$name\Scripts"
        if (Test-Path $scripts) {
            return $scripts
        }
    }

    return $null
}

function Write-MakeShim {
    param(
        [string]$TargetDir,
        [string]$RepoRoot
    )

    $makePs1 = Join-Path $RepoRoot "make.ps1"
    $content = "@echo off`r`nREM NeuroAtlas make shim`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"$makePs1`" %*`r`n"

    foreach ($name in @("make.cmd", "make.bat")) {
        Set-Content -Path (Join-Path $TargetDir $name) -Value $content -Encoding ASCII
    }
}

function Install-ActivateHook {
    param([string]$ActivatePath)

    if (-not (Test-Path $ActivatePath)) {
        return
    }

    $hook = @"

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
    Write-Error "make.cmd not found. cd to repo root or use .\make.cmd <target>."
}
$markerEnd
"@

    $existing = Get-Content $ActivatePath -Raw
    if ($existing -match [regex]::Escape($markerStart)) {
        $pattern = "(?s)$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))"
        $updated = [regex]::Replace($existing, $pattern, $hook.TrimEnd())
    }
    else {
        $updated = $existing.TrimEnd() + $hook
    }

    Set-Content -Path $ActivatePath -Value $updated -Encoding UTF8
    Write-Host "  activate hook: $ActivatePath" -ForegroundColor Green
}

if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

Write-MakeShim -TargetDir $binDir -RepoRoot $repoRoot
Write-Host "OK: repo bin shim -> $binDir\make.cmd" -ForegroundColor Green

$venvScripts = Get-VenvScriptsPath
if ($venvScripts) {
    Write-MakeShim -TargetDir $venvScripts -RepoRoot $repoRoot
    Write-Host "OK: venv shim -> $venvScripts\make.cmd" -ForegroundColor Green
    Install-ActivateHook -ActivatePath (Join-Path $venvScripts "Activate.ps1")
}
else {
    Write-Host "Note: no .venv yet. Create one with: .\make.cmd install" -ForegroundColor Yellow
}

$initScript = Join-Path $repoRoot "scripts\dev\pycharm-terminal-init.ps1"
Write-Host ""
Write-Host "PyCharm (one-time): Settings -> Tools -> Terminal -> Shell path:" -ForegroundColor Cyan
Write-Host "powershell.exe -NoExit -ExecutionPolicy Bypass -File $initScript"
Write-Host ""
Write-Host "Or in THIS terminal right now:" -ForegroundColor Cyan
Write-Host ('  $env:PATH = "' + $binDir + ';" + $env:PATH')
Write-Host "  make help"
