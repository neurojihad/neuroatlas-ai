# Windows make shim — mirrors Makefile targets for PowerShell devs.
# Usage: .\make.ps1 mr_body
#        make mr_body   (when venv make wrapper points here)

param(
    [Parameter(Position = 0)]
    [string]$Target = "help",

    [string]$m = "",
    [string]$k = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host $Message
}

function Invoke-PoetryRun {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)

    if (Get-Command poetry -ErrorAction SilentlyContinue) {
        & poetry run @Command
        return
    }

    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        if ($Command.Length -gt 0 -and $Command[0] -eq "python") {
            $Command = $Command[1..($Command.Length - 1)]
        }
        & $venvPython @Command
        return
    }

    throw "Poetry or .venv not found. Run: pip install poetry; poetry install"
}

function Invoke-Compose {
    param(
        [string[]]$ComposeArgs,
        [switch]$Infra
    )

    $envFile = Join-Path $PSScriptRoot "infra\.env"
    $composeFile = if ($Infra) {
        Join-Path $PSScriptRoot "infra\infra.compose.yml"
    } else {
        Join-Path $PSScriptRoot "infra\application.compose.yml"
    }

    $args = @("compose", "--env-file", $envFile, "-f", $composeFile) + $ComposeArgs
    & docker @args
}

switch ($Target) {
    "help" {
        Write-Step @"
NeuroAtlas Windows make shim. Examples:
  .\make.ps1 mr_body
  .\make.ps1 setup_hooks
  .\make.ps1 test
  .\make.ps1 lint
"@
    }

    "init" {
        $envPath = Join-Path $PSScriptRoot "infra\.env"
        $examplePath = Join-Path $PSScriptRoot "infra\.env.example"
        if (-not (Test-Path $envPath)) {
            Copy-Item $examplePath $envPath
        }
        & $PSCommandPath setup_hooks
    }

    "setup_hooks" {
        git config core.hooksPath .githooks
        Write-Step "Git hooks installed (.githooks/pre-push refreshes MR_BODY.md on push)."
    }

    "mr_body" {
        Invoke-PoetryRun python scripts/generate_mr_body.py
    }

    "install" {
        pip install poetry
        poetry install
    }

    "install_ml" {
        poetry install --with ml
    }

    "run_patients" {
        Invoke-PoetryRun uvicorn patients.main:app --host 0.0.0.0 --port 8001 --reload
    }

    "run_ml" {
        Invoke-PoetryRun uvicorn ml.main:app --host 0.0.0.0 --port 8002 --reload
    }

    "run_housekeeper" {
        Invoke-PoetryRun uvicorn housekeeper.main:app --host 0.0.0.0 --port 8003 --reload
    }

    "up_infra" {
        Invoke-Compose -Infra @("--profile", "storage", "up", "-d")
    }

    "down_infra" {
        Invoke-Compose -Infra @("--profile", "storage", "down")
    }

    "up_app" {
        Invoke-Compose @("up", "-d", "--build")
    }

    "down_app" {
        Invoke-Compose @("down")
    }

    "up" {
        & $PSCommandPath up_infra
        & $PSCommandPath up_app
    }

    "down" {
        & $PSCommandPath down_app
        & $PSCommandPath down_infra
    }

    "kafka_topics" {
        $env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
        Invoke-PoetryRun python infra/kafka/init_topics.py
    }

    "fmt" {
        Invoke-PoetryRun isort --profile black src/
        Invoke-PoetryRun ruff format src
    }

    "fmt_check" {
        Invoke-PoetryRun isort --profile black --check src/
        Invoke-PoetryRun ruff format --check src
    }

    "lint" {
        Invoke-PoetryRun ruff check src
        Invoke-PoetryRun mypy src/
    }

    "lint_fix" {
        Invoke-PoetryRun ruff check --fix src
    }

    "sast" {
        Invoke-PoetryRun bandit -c pyproject.toml -r src
    }

    "check" {
        & $PSCommandPath fmt
        & $PSCommandPath lint
        & $PSCommandPath test
    }

    "test" {
        Invoke-PoetryRun pytest src
    }

    "test_patients" {
        Invoke-PoetryRun pytest src/patients --cov=src/patients
    }

    "test_ml" {
        Invoke-PoetryRun pytest src/ml --cov=src/ml
    }

    "test_housekeeper" {
        Invoke-PoetryRun pytest src/housekeeper --cov=src/housekeeper
    }

    "test_messaging" {
        Invoke-PoetryRun pytest src/common/tests/test_bus src/ml/tests/test_adapters
    }

    "test_in_ci" {
        New-Item -ItemType Directory -Force -Path reports | Out-Null
        $coverage = Join-Path $PSScriptRoot "coverage.xml"
        $junit = Join-Path $PSScriptRoot "reports\junit.xml"
        Invoke-PoetryRun pytest src `
            --cov=src `
            --cov-report=xml:$coverage `
            --cov-report=term `
            --junitxml=$junit `
            --rootdir=$PSScriptRoot `
            -n auto
    }

    "pip_audit" {
        Invoke-PoetryRun pip-audit
    }

    "migrate" {
        Invoke-PoetryRun alembic upgrade head
    }

    "check_migrations" {
        Invoke-PoetryRun alembic check
    }

    "makemigration" {
        if (-not $m) { throw "Usage: .\make.ps1 makemigration -m `"message`"" }
        Invoke-PoetryRun alembic revision --autogenerate -m $m
    }

    "test_k" {
        if (-not $k) { throw "Usage: .\make.ps1 test_k -k `"pattern`"" }
        Invoke-PoetryRun pytest src "-k=$k"
    }

    "relock" {
        poetry lock --no-update
    }

    default {
        throw "Unknown target '$Target'. Run: .\make.ps1 help"
    }
}
