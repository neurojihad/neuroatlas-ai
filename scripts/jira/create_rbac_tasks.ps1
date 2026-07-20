#Requires -Version 5.1
<#
.SYNOPSIS
  Create the Access model / RBAC (IAM service) epic (NLS-EPIC-09) and stories NLS-901..NLS-922.

.DESCRIPTION
  New dedicated hexagonal service src/iam/ (port 8004) implementing RBAC (users/roles/resources).
  Creates one Epic and 22 Story issues linked to it, with the standard NeuroAtlas description
  template (Context / Architecture reference / Acceptance criteria / Out of scope), labels, size,
  and dependency notes. Stories are left in the backlog (never added to an active sprint here).

  Requires JIRA_* credentials in infra/.env. Run '.\scripts\jira\jira_api.ps1 verify' first.

.EXAMPLE
  .\scripts\jira\create_rbac_tasks.ps1
  .\scripts\jira\create_rbac_tasks.ps1 -EpicKey NLS-70   # reuse an existing epic
#>
param(
    [string]$EpicKey = "",
    [string[]]$OnlyRefs = @(),
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiScript = Join-Path $ScriptDir "jira_api.ps1"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

function New-Desc {
    param(
        [string]$Ref,
        [string]$Context,
        [string]$Arch,
        [string[]]$AC,
        [string]$Deps = "none",
        [string]$Size,
        [string[]]$OutOfScope = @()
    )
    $acLines = ($AC | ForEach-Object { "- [ ] $_" }) -join "`n"
    $oosItems = @($OutOfScope | Where-Object { $_ })
    $oosLines = if ($oosItems.Count -gt 0) { ($oosItems | ForEach-Object { "- $_" }) -join "`n" } else { "- Work tracked by dependent stories in this epic" }
    return @"
## Context
$Context

Plan ref: $Ref | Depends on: $Deps | Size: $Size

## Architecture reference
$Arch

## Acceptance criteria
$acLines

## Out of scope
$oosLines
"@
}

$Stories = @(
    @{
        Ref = "NLS-901"; Size = "S"; Deps = "none"; Labels = @("backend")
        Title = "Add DatabaseException adapter-layer exception"
        Arch = "docs/ARCHITECTURE.md section 12 - layered exception model (backend_conventions marks DatabaseException 'future')"
        Context = "RBAC adapters must wrap infra failures in DatabaseException(msg, details). This is the future adapter-layer exception referenced by backend_conventions."
        AC = @(
            "Add DatabaseException(message, details=None) to common/core/exceptions.py mirroring BusException",
            "register_exception_handlers maps it to a 500 ErrorSchema (details logged, not leaked)",
            "Domain never raises it; adapters raise it and it re-raises through tasks/consumers",
            "Unit test for handler mapping and error envelope"
        )
        OutOfScope = @("Concrete DB adapter wiring (covered by NLS-911)")
    },
    @{
        Ref = "NLS-902"; Size = "M"; Deps = "none (cross-link NLS-701)"; Labels = @("backend", "infra")
        Title = "db_measure metrics decorator + CrudOperation enum"
        Arch = "docs/ARCHITECTURE.md section 12 - observability; cross-link NLS-701 Prometheus metrics"
        Context = "Reference adapter methods are decorated @db_measure(CrudOperation.X, ORM). Introduce a prometheus-backed equivalent in the adapter/app layer (never domain)."
        AC = @(
            "CrudOperation StrEnum (CREATE/READ/UPDATE/DELETE/UPSERT/LIST) in common/adapters/metrics/",
            "db_measure(op, backend_label) records a latency Histogram + count Counter with labels {operation,backend,result} via prometheus-client",
            "Async support; result='error' on exception then re-raise",
            "No domain import of the decorator (architecture check)",
            "Unit tests for success and error paths"
        )
        OutOfScope = @("Mounting /metrics ASGI app (NLS-701)")
    },
    @{
        Ref = "NLS-903"; Size = "S"; Deps = "none"; Labels = @("backend")
        Title = "Cursor pagination helper + ext_str util"
        Arch = "docs/ARCHITECTURE.md section 12 - shared common utilities; PaginatedResponseSchema"
        Context = "list_users/list_resources use cursor pagination; the reference adapter uses ext_str(exc) for detail formatting."
        AC = @(
            "PaginatorResult (items + next cursor) and cursor_paginate(...) in common/utils/pagination.py with an opaque cursor and stable ordering",
            "Maps onto the existing PaginatedResponseSchema (data + next)",
            "ext_str(exc) -> str util in common/utils",
            "Unit tests for forward paging, empty page, terminal cursor None"
        )
    },
    @{
        Ref = "NLS-904"; Size = "M"; Deps = "none"; Labels = @("backend", "infra")
        Title = "IAM service scaffold (src/iam/)"
        Arch = "docs/ARCHITECTURE.md section 12 - hexagonal service layout; section 5 Phase 4"
        Context = "New hexagonal service built via common.application.app_factory.create(...), port 8004, offline-safe lazy engine startup. Decision D1: dedicated src/iam/ (not common/ or admin_ui/)."
        AC = @(
            "main.py / lifespan.py / settings.py present; IamSettings(Settings) with service_name='iam', postgres_uri, redis_url, port",
            "/health works",
            "make run_iam runs locally with in-memory UoW",
            "pyproject.toml gains an iam dependency group",
            "tests/ package present",
            "Service starts with AUTH_ENABLED=false and Postgres down"
        )
        OutOfScope = @("Docker/compose wiring (NLS-921)")
    },
    @{
        Ref = "NLS-905"; Size = "S"; Deps = "NLS-904"; Labels = @("backend", "auth")
        Title = "RBAC domain entities"
        Arch = "docs/ARCHITECTURE.md section 5 Phase 4 - access model; section 12 domain layering"
        Context = "Pure dataclasses User(id,email,role_id), Role(id,name,description), Resource(id,name), RoleResource(role_id,resource_id); no framework imports. Decision D2: ULID PKs with prefixes usr_/rol_/res_."
        AC = @(
            "iam/domain/entities.py frozen dataclasses with ULID-prefixed ids (D2)",
            "iam/domain/exceptions.py service-specific DomainError subclasses (e.g. RoleInUse)",
            "No FastAPI/SQLAlchemy/adapter imports"
        )
    },
    @{
        Ref = "NLS-906"; Size = "M"; Deps = "NLS-905"; Labels = @("backend", "auth")
        Title = "AccessModelRepository + AccessModelUnitOfWork ports"
        Arch = "docs/ARCHITECTURE.md section 12 - ports and adapters (mirror patients ports)"
        Context = "Declare the abstract repository (full method set) plus a UoW port exposing it, mirroring patients ports."
        AC = @(
            "iam/domain/ports/access_model.py abc: create_or_update, update_user, delete_user, get_user(email?/user_id?), list_users(limit,cursor)",
            "role methods: create_role, update_role, delete_role, get_role, get_all_roles",
            "resource methods: create_resource, update_resource, delete_resource, get_resource_by_name, list_resources(role_id?)",
            "link methods: is_role_resource_exists, create_role_resource, delete_role_resource",
            "iam/domain/ports/uow.py AccessModelUnitOfWork(UnitOfWork) exposes access_model + copy(); no infra imports"
        )
    },
    @{
        Ref = "NLS-907"; Size = "L"; Deps = "NLS-906, NLS-903"; Labels = @("backend", "auth")
        Title = "RBAC domain commands + queries"
        Arch = "docs/ARCHITECTURE.md section 12 - Commands/Queries; backend_conventions business-logic rules"
        Context = "Writes as Command subclasses (frozen Context + validate_context + async execute inside 'async with self.uow'); reads as async funcs in queries.py raising NotFound."
        AC = @(
            "Commands: CreateOrUpdateUser, UpdateUser, DeleteUser, CreateRole, UpdateRole, DeleteRole, CreateResource, UpdateResource, DeleteResource, LinkRoleResource, UnlinkRoleResource (CommandResult[T], context validation of email/name/id-prefix)",
            "Queries: get_user, list_users(limit,cursor), get_role, get_all_roles, get_resource_by_name, list_resources(role_id?), is_role_resource_exists (NotFound on missing)",
            "LinkRoleResource idempotent-guarded via is_role_resource_exists",
            "list_* use the cursor helper (NLS-903)",
            "Covered by fake tests (NLS-918)"
        )
        OutOfScope = @("HTTP surface (NLS-916)")
    },
    @{
        Ref = "NLS-908"; Size = "S"; Deps = "NLS-907, NLS-901"; Labels = @("backend")
        Title = "IAM domain/tasks.py orchestration stub"
        Arch = "docs/ARCHITECTURE.md section 12 - exception-orchestration rule (paymentgate tasks.py parity)"
        Context = "paymentgate-parity tasks.py for background/event orchestration; a documented stub following the exception-orchestration rule."
        AC = @(
            "iam/domain/tasks.py with try/except skeleton (DatabaseException/BusException re-raised, others logged via logger.aexception)",
            "Placeholder task sync_user_role delegating to a command",
            "No live wiring",
            "Unit test: infra errors propagate, generic errors contained"
        )
    },
    @{
        Ref = "NLS-909"; Size = "M"; Deps = "NLS-905"; Labels = @("backend", "infra")
        Title = "RBAC ORM models + extend UserORM"
        Arch = "docs/ARCHITECTURE.md section 5 - auth users schema; section 12 persistence"
        Context = "Add RoleORM/ResourceORM/RoleResourceORM in common/adapters/database/models/ plus a nullable role_id FK on UserORM. Decisions D3 (extend existing UserORM, no second users table) and D5 (models in common so Alembic autogenerate sees them)."
        AC = @(
            "roles(id PK str, name unique, description), resources(id PK str, name unique), role_resources(role_id FK, resource_id FK, composite PK, cascade delete) on the shared Base",
            "UserORM gains role_id Mapped[str|None] FK->roles.id (ON DELETE SET NULL) + relationship; existing columns untouched",
            "Models importable without a DB",
            "Naming/index consistent with user.py"
        )
    },
    @{
        Ref = "NLS-910"; Size = "M"; Deps = "NLS-909"; Labels = @("infra", "backend")
        Title = "Alembic migration 0003_rbac"
        Arch = "docs/ARCHITECTURE.md section 4 Housekeeper - centralized Alembic env"
        Context = "New tables plus users.role_id column in the centralized housekeeper Alembic env."
        AC = @(
            "src/housekeeper/migrations/versions/0003_rbac.py (down_revision='0002_users') creates roles/resources/role_resources and ALTER TABLE users ADD COLUMN role_id with FK/index",
            "Full downgrade()",
            "migrations/env.py imports the new model modules",
            "make migrate applies cleanly",
            "make makemigration autogenerate shows no unexpected diff afterwards"
        )
    },
    @{
        Ref = "NLS-911"; Size = "L"; Deps = "NLS-909, NLS-902, NLS-903, NLS-901, NLS-906"; Labels = @("backend", "auth")
        Title = "SQLAlchemyAccessModelRepository (postgres.py)"
        Arch = "docs/ARCHITECTURE.md section 12 - persistence adapters (mirror PostgresUserRepository)"
        Context = "Concrete adapter implementing every port method with AsyncSession (Decision D4), pg upsert for create_or_update, cursor pagination, @db_measure, DatabaseException(msg, ext_str(exc)) wrapping, and _map_row_to_user/role/resource mappers."
        AC = @(
            "All port methods implemented against the ORM models",
            "create_or_update uses pg_insert.on_conflict_do_update(index_elements=[email], set_={role_id, updated_at})",
            "list_users/list_resources(role_id?) use cursor pagination (NLS-903); list_resources joins role_resources when role_id is given",
            "Each method @db_measure(CrudOperation.X, 'sqlalchemy')",
            "All failures wrapped in DatabaseException(msg, ext_str(exc)); row mappers translate ORM->entities; no DomainError raised from the adapter"
        )
    },
    @{
        Ref = "NLS-912"; Size = "S"; Deps = "NLS-911"; Labels = @("backend")
        Title = "SQLAlchemy IAM Unit of Work"
        Arch = "docs/ARCHITECTURE.md section 12 - unit of work (SqlAlchemyUnitOfWork)"
        Context = "SqlAlchemyAccessModelUnitOfWork(SqlAlchemyUnitOfWork) attaches the repo in __aenter__."
        AC = @(
            "Subclasses common.database.sqlalchemy_uow.SqlAlchemyUnitOfWork",
            "__aenter__ calls super then sets self.access_model = SQLAlchemyAccessModelRepository(self.session)",
            "copy() returns a fresh UoW over the same session factory",
            "commit-on-clean-exit / rollback-on-exception verified by test"
        )
    },
    @{
        Ref = "NLS-913"; Size = "M"; Deps = "NLS-904 (cross-link NLS-104, NLS-506)"; Labels = @("infra", "backend")
        Title = "Redis cache adapter + wiring"
        Arch = "docs/ARCHITECTURE.md section 6 Redis; cross-link NLS-104 / NLS-506"
        Context = "redis.py adapter for a CachePort - the first Redis use - for role/resource lookup caching plus future sessions/rate-limit."
        AC = @(
            "iam/domain/ports/cache.py CachePort (get/set/delete/ttl) and iam/adapters/redis.py RedisCache (redis.asyncio)",
            "redis dependency in the iam/common group; IamSettings.redis_url",
            "Wired in lifespan onto app.state.cache with lazy connect",
            "infra/application.compose.yml adds a redis service + .env(.example) keys + healthcheck on neuroatlasnet",
            "Cache failures degrade gracefully (miss, not crash), wrapped/logged, never DomainError",
            "Fake in-memory CachePort for tests"
        )
    },
    @{
        Ref = "NLS-914"; Size = "S"; Deps = "NLS-904, NLS-901"; Labels = @("backend", "gateway")
        Title = "Outbound gateways/ HTTP client scaffold"
        Arch = "docs/ARCHITECTURE.md section 12 - outbound gateways (reuse admin_ui httpx.AsyncClient pattern)"
        Context = "paymentgate-parity outbound HTTP client (e.g. Keycloak admin / other services), reusing the httpx.AsyncClient pattern from admin_ui."
        AC = @(
            "iam/domain/ports/gateway.py port and iam/adapters/gateways/http_client.py adapter (httpx.AsyncClient, timeouts, error -> GatewayException per ADR, not DomainError)",
            "Wired in lifespan, closed on shutdown",
            "Fake gateway double + unit test"
        )
    },
    @{
        Ref = "NLS-915"; Size = "S"; Deps = "NLS-904"; Labels = @("backend")
        Title = "email/ notification adapter scaffold"
        Arch = "docs/ARCHITECTURE.md section 12 - notifier port (paymentgate parity)"
        Context = "paymentgate-parity notifier port + a minimal adapter (log/SMTP stub) for RBAC events."
        AC = @(
            "iam/domain/ports/notifier.py Notifier port and iam/adapters/email/smtp_notifier.py (log-only default, SMTP optional)",
            "Domain calls the port only",
            "Adapter wraps failures per the exception rule",
            "Fake notifier + unit test"
        )
    },
    @{
        Ref = "NLS-916"; Size = "M"; Deps = "NLS-907, NLS-917, NLS-903"; Labels = @("backend", "auth")
        Title = "IAM HTTP adapter (router, schemas, deps)"
        Arch = "docs/ARCHITECTURE.md section 12 - HTTP adapters; ResponseSchema/PaginatedResponseSchema"
        Context = "Thin FastAPI surface for users/roles/resources/links; handlers build Context, run command/query, wrap in ResponseSchema/PaginatedResponseSchema."
        AC = @(
            "adapters/http/handlers.py CRUD for users/roles/resources + link/unlink + list with cursor, mounted via app_factory",
            "adapters/http/schemas.py Pydantic I/O; list returns PaginatedResponseSchema (data + next)",
            "adapters/http/dependencies.py provides uow/cache/current-user via Depends (mirror patients unit_of_work)",
            "No business logic in handlers; DomainError mapped by register_exception_handlers",
            "Handler tests against a fake UoW"
        )
    },
    @{
        Ref = "NLS-917"; Size = "M"; Deps = "NLS-906"; Labels = @("backend")
        Title = "Fake in-memory access model (repo + UoW)"
        Arch = "docs/ARCHITECTURE.md section 12 - in-memory adapters (mirror patients in_mem.py)"
        Context = "Explicit testability requirement - mirror patients in_mem.py + housekeeper FakeDatabaseMonitor so the domain is testable without Postgres."
        AC = @(
            "iam/adapters/database/in_mem.py FakeAccessModelRepository (full port over process dicts incl. cursor pagination + is_role_resource_exists)",
            "FakeAccessModelUnitOfWork(AccessModelUnitOfWork) with no-op commit/rollback + copy()",
            "reset_store() clears shared state",
            "Behavior parity with the SQLAlchemy adapter for tested paths (same NotFound/pagination semantics)"
        )
    },
    @{
        Ref = "NLS-918"; Size = "M"; Deps = "NLS-907, NLS-917"; Labels = @("backend")
        Title = "Domain unit tests against fakes + conftest"
        Arch = "docs/ARCHITECTURE.md section 12 - tests (asyncio_mode=auto, mirror module paths)"
        Context = "pytest asyncio_mode=auto, test_* under src/iam/tests/ mirroring module paths; autouse fixture resets the fake store."
        AC = @(
            "src/iam/tests/conftest.py autouse reset_store fixture (mirror patients)",
            "tests/test_domain/ cover all commands + queries (happy, validation errors, NotFound, idempotent link, cursor paging)",
            "Coverage omits __init__/settings/domain/ports/tests",
            "make test_iam green with no infra"
        )
    },
    @{
        Ref = "NLS-919"; Size = "S"; Deps = "NLS-916, NLS-917"; Labels = @("backend", "auth")
        Title = "Smoke test on FakeUnitOfWork (no Postgres)"
        Arch = "docs/ARCHITECTURE.md section 12 - smoke tests use FakeUnitOfWork"
        Context = "Explicit 'smoke tests use FakeUnitOfWork' requirement - an e2e command->query flow through the app with the fake wired."
        AC = @(
            "Smoke test wires FakeAccessModelUnitOfWork onto app.state.uow_factory",
            "Exercises create role -> create resource -> link -> create/upsert user with role -> list users (cursor) -> get_user",
            "Runs with AUTH_ENABLED=false, no Postgres/Redis, deterministic",
            "Part of make test"
        )
    },
    @{
        Ref = "NLS-920"; Size = "M"; Deps = "NLS-911, NLS-912, NLS-910"; Labels = @("backend", "infra")
        Title = "SQLAlchemy adapter integration tests (marked, Postgres)"
        Arch = "docs/ARCHITECTURE.md section 12 - adapter integration tests; CI gates"
        Context = "Adapter-level tests for upsert/pagination/mapper correctness against real Postgres; marked so default CI can skip."
        AC = @(
            "tests/integration/ for create_or_update upsert, list_users/list_resources cursor+join, delete cascade, row mappers, DatabaseException wrapping on forced failure",
            "pytest marker @pytest.mark.integration + fixture for Postgres",
            "Excluded from the default make test_iam"
        )
    },
    @{
        Ref = "NLS-921"; Size = "M"; Deps = "NLS-904, NLS-913"; Labels = @("infra")
        Title = "IAM Docker/compose/Makefile wiring"
        Arch = "docs/ARCHITECTURE.md section 12 - per-service Dockerfile + compose + Make targets"
        Context = "Ship the service like the others (non-root Dockerfile, compose entry, Make targets, env keys)."
        AC = @(
            "src/iam/Dockerfile (non-root, poetry install --only main,iam[,messaging])",
            "infra/application.compose.yml adds iam (port 8004) on neuroatlasnet with --env-file infra/.env",
            "make up_iam/down/run_iam/test_iam targets",
            "infra/.env.example(+.env) gain IAM_*, REDIS_URL, iam POSTGRES_URI keys",
            "make check + make sast pass for src/iam/"
        )
    },
    @{
        Ref = "NLS-922"; Size = "S"; Deps = "finalize after NLS-910 (D-decisions ratified early)"; Labels = @("backend", "auth", "infra")
        Title = "ADR + docs update (id strategy, UserORM reconciliation, RBAC schema)"
        Arch = "docs/ARCHITECTURE.md section 5 / section 6 - RBAC as Phase-4 layer atop JWT realm roles"
        Context = "Record decisions D1-D5 and align docs so RBAC does not contradict 'roles from JWT' (ARCHITECTURE section 5) - DB RBAC is the Phase-4 fine-grained layer atop JWT realm roles."
        AC = @(
            "ADR under docs/ capturing D1-D5 (service placement, ULID PKs, UserORM extension + migration impact, AsyncSession, models-in-common)",
            "ARCHITECTURE.md section 5/6 updated (RBAC = Phase-4 resource policies + auth-users-schema note for role_id/roles/resources/role_resources)",
            "docs/jira/plan.md + backlog-keys.md updated with the new epic/stories (status Open)"
        )
    }
)

Write-Output "=== Access model / RBAC (IAM service) - NLS-EPIC-09 ==="
Write-Output ("Stories to create: {0}" -f $Stories.Count)
Write-Output ""

if ($DryRun) {
    Write-Output "(dry run - no Jira writes)"
    foreach ($s in $Stories) {
        Write-Output ("{0} [{1}] {2}  ({3})" -f $s.Ref, $s.Size, $s.Title, ($s.Labels -join ","))
    }
    return
}

# 1. Epic
if (-not $EpicKey) {
    $epicDesc = @"
## Context
Access model / RBAC via a new dedicated hexagonal service src/iam/ (port 8004): users, roles, resources, and role-resource links. DB RBAC is the Phase-4 fine-grained authorization layer atop Keycloak JWT realm roles. Cross-links EPIC-03 (Identity & audit), EPIC-07 (Observability), and NLS-104/NLS-506 (Redis).

Key decisions:
D1 Dedicated src/iam/ service (not common/ or admin_ui/).
D2 ULID string PKs with prefixes usr_/rol_/res_; RoleResource composite PK.
D3 Extend existing common UserORM with nullable role_id FK -> roles (ON DELETE SET NULL); no second users table.
D4 Use AsyncSession (subclass SqlAlchemyUnitOfWork), not AsyncConnection.
D5 New ORM models live in common/adapters/database/models/ so Alembic autogenerate (housekeeper) sees them.

## Architecture reference
docs/ARCHITECTURE.md section 5 Phase 4, section 6 Redis, section 12

## Acceptance criteria
- [ ] Stories NLS-901..NLS-922 delivered per dependency-ordered milestones M-A..M-E
- [ ] src/iam/ service runs offline (AUTH_ENABLED=false, no Postgres/Redis) and via compose (port 8004)
- [ ] RBAC schema migrated (roles/resources/role_resources + users.role_id) and documented in an ADR

## Out of scope
- Keycloak realm-role provisioning (EPIC-03)
- Gateway rate limiting (NLS-104)
"@
    Write-Output "Creating epic NLS-EPIC-09..."
    $out = & $ApiScript create -Type Epic -Summary "Access model / RBAC (IAM service)" -Description $epicDesc -Labels @("backend", "auth", "infra")
    $line = $out | Where-Object { $_ -match "^Created:" } | Select-Object -First 1
    if ($line -match "Created:\s+(\S+)") {
        $EpicKey = $Matches[1]
        Write-Output ("NLS-EPIC-09 -> {0}" -f $EpicKey)
    }
    else {
        throw "Failed to create epic: $out"
    }
}
else {
    Write-Output ("Reusing epic {0}" -f $EpicKey)
}

Write-Output ""
Write-Output "=== Creating stories ==="
$Created = @()
$onlySet = @($OnlyRefs | Where-Object { $_ })
foreach ($s in $Stories) {
    if ($onlySet.Count -gt 0 -and ($onlySet -notcontains $s.Ref)) {
        continue
    }
    $oos = if ($s.ContainsKey('OutOfScope')) { $s.OutOfScope } else { @() }
    $desc = New-Desc -Ref $s.Ref -Context $s.Context -Arch $s.Arch -AC $s.AC -Deps $s.Deps -Size $s.Size -OutOfScope $oos
    $out = & $ApiScript create -Type Story -Summary $s.Title -Epic $EpicKey -Description $desc -Labels $s.Labels
    $line = $out | Where-Object { $_ -match "^Created:" } | Select-Object -First 1
    if ($line -match "Created:\s+(\S+)") {
        $key = $Matches[1]
        $Created += [pscustomobject]@{ Ref = $s.Ref; JiraKey = $key; Title = $s.Title; Labels = ($s.Labels -join ",") }
        Write-Output ("{0} -> {1}  [{2}]" -f $s.Ref, $key, ($s.Labels -join ","))
    }
    else {
        throw "Failed to create $($s.Ref): $out"
    }
}

Write-Output ""
Write-Output "=== Done ==="
Write-Output ("Epic {0}; created {1} stories." -f $EpicKey, $Created.Count)
Write-Output ""
Write-Output "MAPPING_START"
Write-Output ("EPIC|NLS-EPIC-09|{0}|Access model / RBAC (IAM service)" -f $EpicKey)
foreach ($row in $Created) {
    Write-Output ("STORY|{0}|{1}|{2}" -f $row.Ref, $row.JiraKey, $row.Title)
}
Write-Output "MAPPING_END"
