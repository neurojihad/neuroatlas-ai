# One-shot Windows setup: make fmt in PyCharm Terminal.
# Usage:  .\make.cmd setup_make

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$binDir = Join-Path $repoRoot "bin"

Write-Host "NeuroAtlas make setup..." -ForegroundColor Cyan
Write-Host ""

& (Join-Path $PSScriptRoot "install-venv-make.ps1")

Write-Host ""
Write-Host "Quick test:" -ForegroundColor Yellow
Write-Host ('  $env:PATH = "' + $binDir + ';" + $env:PATH')
Write-Host "  make help"
