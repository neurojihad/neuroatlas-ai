# Windows make shim - mirrors Makefile targets for PowerShell (paymentgate-style).
# Do NOT paste Makefile lines into PowerShell; use this script instead.
#
#   .\make.ps1 up_infra
#   .\make.ps1 migrate
#   .\make.ps1 run_patients
#
# Or from repo root:  make.cmd up_infra

param(
    [Parameter(Position = 0)]
    [string]$Target = "help",

    [string]$m = "",
    [string]$k = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) {
            return
        }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path "Env:$name" -Value $value
    }
}

function Initialize-MakeEnvironment {
    $src = Join-Path $PSScriptRoot "src"
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$src;$($env:PYTHONPATH)"
    } else {
        $env:PYTHONPATH = $src
    }
    Import-DotEnv (Join-Path $PSScriptRoot "infra\.env")
}

function Write-Step {
    param([string]$Message)
    Write-Host $Message
}

$script:DockerPathInitialized = $false

function Add-DirectoryToPath {
    param([string]$Directory)

    if (-not $Directory -or -not (Test-Path $Directory)) {
        return
    }
    $parts = $env:PATH -split ';' | Where-Object { $_ -and ($_ -ne $Directory) }
    $env:PATH = ($Directory, ($parts -join ';') | Where-Object { $_ }) -join ';'
}

function Initialize-DockerPath {
    if ($script:DockerPathInitialized) {
        return
    }

    foreach ($binDir in @(
            "${env:ProgramFiles}\Docker\Docker\resources\bin"
            "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin"
            "${env:ProgramFiles}\Docker\Docker\cli-plugins"
            "${env:LOCALAPPDATA}\Docker\cli-plugins"
        )) {
        Add-DirectoryToPath $binDir
    }

    $script:DockerPathInitialized = $true
}

function Resolve-DockerExecutable {
    Initialize-DockerPath

    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    foreach ($candidate in @(
            "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe"
            "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe"
        )) {
        if (Test-Path $candidate) {
            Add-DirectoryToPath (Split-Path $candidate -Parent)
            return $candidate
        }
    }

    throw @'
docker was not found in PATH or Docker Desktop default locations.

Install Docker Desktop for Windows:
  https://docs.docker.com/desktop/setup/install/windows-install/

Start Docker Desktop, then open a NEW PowerShell window and retry.

Do not paste Makefile lines like "$(COMPOSE_INFRA) --profile storage up -d" into PowerShell - run:
  .\make.ps1 up_infra
  make.cmd up_infra
'@
}

function Invoke-PoetryRun {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)

    if (Get-Command poetry -ErrorAction SilentlyContinue) {
        & poetry run @Command
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        return
    }

    $venvScripts = Join-Path $PSScriptRoot ".venv\Scripts"
    $venvPython = Join-Path $venvScripts "python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "Poetry or .venv not found. Run: .\make.ps1 install"
    }

    # poetry run --with <group> python ... (venv fallback: dev deps should already be installed)
    if ($Command.Length -ge 3 -and $Command[0] -eq "--with") {
        $Command = @($Command[2..($Command.Length - 1)])
    }

    if ($Command.Length -gt 0 -and $Command[0] -eq "python") {
        & $venvPython @($Command[1..($Command.Length - 1)])
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        return
    }

    if ($Command.Length -eq 0) {
        throw "Invoke-PoetryRun: empty command"
    }

    $toolExe = Join-Path $venvScripts "$($Command[0]).exe"
    if (Test-Path $toolExe) {
        & $toolExe @($Command[1..($Command.Length - 1)])
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        return
    }

    & $venvPython -m @Command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Compose {
    param(
        [string[]]$ComposeArgs,
        [switch]$Infra
    )

    $docker = Resolve-DockerExecutable
    $envFile = Join-Path $PSScriptRoot "infra\.env"
    if (-not (Test-Path $envFile)) {
        throw "Missing infra/.env. Run: .\make.ps1 init"
    }
    $composeFile = if ($Infra) {
        Join-Path $PSScriptRoot "infra\infra.compose.yml"
    } else {
        Join-Path $PSScriptRoot "infra\application.compose.yml"
    }

    $args = @("compose", "--env-file", $envFile, "-f", $composeFile) + $ComposeArgs
    & $docker @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Initialize-MakeEnvironment

switch ($Target) {
    "help" {
        Write-Step @'
NeuroAtlas Windows make shim (mirrors Makefile).

Infra / Docker:
  .\make.ps1 init              copy infra/.env.example to infra/.env
  .\make.ps1 up_infra          Postgres + Kafka + Keycloak
  .\make.ps1 down_infra
  .\make.ps1 keycloak_ensure   reconcile neuroatlas-ui client (stale volume fix)
  .\make.ps1 reset_keycloak    wipe Keycloak data + re-import realm
  .\make.ps1 up_app            build and start app services (browser: http://localhost:8000)
  .\make.ps1 down_app
  .\make.ps1 up_admin / down_admin
  .\make.ps1 up                up_infra then up_app
  .\make.ps1 down              down_app then down_infra
  .\make.ps1 up_pat / down_pat / up_ml / down_ml / up_hk / down_hk
  .\make.ps1 kafka_topics
  .\make.ps1 kafka_logs

Run locally (no Docker):
  .\make.ps1 run_admin_ui     port 8000
  .\make.ps1 run_patients      port 8001
  .\make.ps1 run_ml            port 8002
  .\make.ps1 run_housekeeper   port 8003

DB:
  .\make.ps1 migrate           alembic upgrade head (needs up_infra)
  .\make.ps1 makemigration -m "add table"

Quality:
  .\make.ps1 test / lint / fmt / check / sast
  .\make.ps1 smoke_admin_ui   NLS-68 E2E smoke (live stack; see docs/smoke/admin-ui-e2e.md)

Windows / PyCharm (once):
  .\make.ps1 setup_make       install make into .venv (then: make fmt in new terminal)

Shortcut:  make.cmd up_infra   (same as .\make.ps1 up_infra)
'@
    }

    "init" {
        $envPath = Join-Path $PSScriptRoot "infra\.env"
        $examplePath = Join-Path $PSScriptRoot "infra\.env.example"
        if (-not (Test-Path $envPath)) {
            Copy-Item $examplePath $envPath
        }
        & $PSCommandPath setup_hooks
        & $PSCommandPath setup_make
    }

    "setup_make" {
        & (Join-Path $PSScriptRoot "scripts\dev\setup-pycharm-make.ps1")
    }

    "setup_hooks" {
        git config core.hooksPath .githooks
        Write-Step "Git hooks installed (.githooks/pre-push refreshes MR_BODY.md + Default.md on push)."
    }

    "mr_body" {
        Invoke-PoetryRun python scripts/generate_mr_body.py
    }

    "install" {
        pip install poetry
        poetry install
        & (Join-Path $PSScriptRoot "scripts\dev\install-venv-make.ps1")
    }

    "install_ml" {
        poetry install --with ml
    }

    "run_admin_ui" {
        Invoke-PoetryRun uvicorn admin_ui.main:app --host 0.0.0.0 --port 8000 --reload
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

    "keycloak_ensure" {
        Invoke-Compose -Infra @("--profile", "storage", "up", "keycloak-init")
    }

    "reset_keycloak" {
        Invoke-Compose -Infra @("--profile", "storage", "rm", "-sf", "keycloak", "keycloak-init")
        $docker = Resolve-DockerExecutable
        & $docker volume rm neuroatlas-infra_keycloak_data 2>$null
        Invoke-Compose -Infra @("--profile", "storage", "up", "-d", "keycloak")
        & $PSCommandPath keycloak_ensure
    }

    "up_app" {
        Write-Step "Browser entry: http://localhost:8000 (Keycloak: run up_infra first)"
        Invoke-Compose @("up", "-d", "--build")
    }

    "down_app" {
        Invoke-Compose @("down")
    }

    "up_admin" {
        Invoke-Compose @("up", "-d", "--build", "admin_ui")
    }

    "down_admin" {
        Invoke-Compose @("stop", "admin_ui")
    }

    "up" {
        & $PSCommandPath up_infra
        & $PSCommandPath up_app
    }

    "down" {
        & $PSCommandPath down_app
        & $PSCommandPath down_infra
    }

    "up_pat" {
        Invoke-Compose @("up", "-d", "--build", "patients")
    }

    "down_pat" {
        Invoke-Compose @("stop", "patients")
    }

    "up_ml" {
        Write-Step "ML Kafka consumer is active only when KAFKA_ENABLED=true in infra/.env"
        Invoke-Compose @("up", "-d", "--build", "ml")
    }

    "down_ml" {
        Invoke-Compose @("stop", "ml")
    }

    "up_hk" {
        Invoke-Compose @("up", "-d", "--build", "housekeeper")
    }

    "down_hk" {
        Invoke-Compose @("stop", "housekeeper")
    }

    "kafka_topics" {
        $env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
        Invoke-PoetryRun --with messaging python infra/kafka/init_topics.py
    }

    "kafka_logs" {
        $docker = Resolve-DockerExecutable
        & $docker logs -f kafka_neuroatlas
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

    "test_admin_ui" {
        Invoke-PoetryRun pytest src/admin_ui --cov=src/admin_ui
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

    "smoke_admin_ui" {
        $env:SMOKE_INTEGRATION = "1"
        Invoke-PoetryRun pytest src/common/tests/integration -m integration -v
    }

    "relock" {
        poetry lock --no-update
    }

    default {
        throw "Unknown target '$Target'. Run: .\make.ps1 help"
    }
}
