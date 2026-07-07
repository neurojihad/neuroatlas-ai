# PyCharm terminal bootstrap - adds repo bin/ to PATH.
# Settings -> Tools -> Terminal -> Shell path:
#   powershell.exe -NoExit -ExecutionPolicy Bypass -File C:\Dev\neuroatlas-ai\scripts\dev\pycharm-terminal-init.ps1

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$binDir = Join-Path $repoRoot "bin"

if ($env:PATH -notlike "*$binDir*") {
    $env:PATH = "$binDir;$env:PATH"
}

$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
}

Write-Host "NeuroAtlas ready: make fmt | make lint | make check" -ForegroundColor Green
