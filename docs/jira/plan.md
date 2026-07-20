# NeuroAtlas — Jira Backlog Plan

Ticket names for creating epics/stories in Jira. Keys (`NLS-xxx`) are **suggested** — adjust to your
project prefix. Link each ticket to [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §12 for context.

**Status key:** `Open` = not started · `Partial` = scaffold exists · `Done` = complete (update as you track)

---

## Epic: NLS-EPIC-01 — Microservice foundation

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-101 | API Gateway service (FastAPI entry point) | Partial | §12, §5 Phase 2 — see NLS-GW-01 |
| NLS-102 | Gateway routing to patients / ml / housekeeper | Open | §4 Gateway — see NLS-GW-02 |
| NLS-103 | Centralize OIDC auth at gateway | Open | §5 Phase 2 — see NLS-GW-04..05 |
| NLS-104 | Rate limiting at gateway (Redis-backed) | Open | §4 Gateway, §6 Redis |
| NLS-105 | Per-service Docker deploy targets in CI | Open | §12 |
| NLS-106 | Database-per-service strategy (design + ADR) | Open | §12 |

---

## Epic: NLS-EPIC-02 — Clinical data (Patients)

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-201 | Patients SQLAlchemy adapter (replace in-memory UoW) | Partial | §12 |
| NLS-202 | Alembic migrations: patients + assessments tables | Open | §4, Housekeeper |
| NLS-203 | Patients service integration tests against Postgres | Open | §12 |
| NLS-204 | Patient-level ACL (auth Phase 4) | Open | §5 Phase 4 |

---

## Epic: NLS-EPIC-03 — Identity & audit

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-301 | Keycloak realm bootstrap (`neuroatlas`, roles, client) | Partial | §5, §6 Keycloak — compose import + volume; manual user still required |
| NLS-302 | Shadow `users` table JIT upsert in production path | Partial | §5, `docs/diagrams/` — wired; needs API call with Bearer |
| NLS-303 | Audit events table + correlation with `user_id` | Open | §5 |
| NLS-304 | Service accounts (client credentials) for ML | Open | §5 Phase 3 |

---

## Epic: NLS-EPIC-04 — Event backbone

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-401 | Kafka topic bootstrap automation in CI | Partial | §7 |
| NLS-402 | Transactional outbox pattern in `common/` | Open | §12 |
| NLS-403 | Saga design for prediction-requested flow | Open | §7, §12 |
| NLS-404 | Dead-letter / retry policy for consumers | Open | §12 |

---

## Epic: NLS-EPIC-05 — Knowledge base (RAG pipeline)

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-501 | Ingestion service — PubMed import | Open | §4 Ingestion, §10 Phase 2 |
| NLS-502 | Article storage schema + chunking | Open | §10 Phase 2 |
| NLS-503 | Embedding service — vector generation | Open | §4 Embedding, §10 Phase 3 |
| NLS-504 | Search service — pgvector semantic retrieval | Open | §4 Search, §10 Phase 4 |
| NLS-505 | LLM Orchestrator — RAG + citations | Open | §4, §10 Phase 4 |
| NLS-506 | Redis cache for search / LLM responses | Open | §6 Redis |

---

## Epic: NLS-EPIC-06 — Machine learning

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-601 | ML Kafka consumer hardening (prod config) | Partial | §4 ML |
| NLS-602 | XGBoost production predictor adapter | Open | §4 ML, §10 Phase 6 |
| NLS-603 | SHAP explainability endpoint | Open | §4 ML |
| NLS-604 | Clinical feature store schema | Open | §3 |

---

## Epic: NLS-EPIC-07 — Observability & ops

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-701 | Prometheus `/metrics` on all services | Open | §12 |
| NLS-702 | Distributed tracing (OpenTelemetry) | Open | §12 |
| NLS-703 | Housekeeper long-query monitoring (Postgres) | Partial | §4 Housekeeper |
| NLS-704 | Structured audit log export | Open | §12 |
| NLS-705 | Self-hosted GitLab Runner (docker executor, project-locked) | Partial | §12, `docs/ci/self-hosted-runner.md` |

---

## Epic: NLS-EPIC-08 — Frontend

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-801 | Next.js app scaffold | Open | §10 Phase 5 |
| NLS-802 | Keycloak login flow in UI | Open | §5 — see NLS-GW-07 (OIDC redirect + PKCE) |
| NLS-803 | Gateway integration from UI | Open | §10 Phase 5 — see NLS-GW-08 |

---

## Epic: NLS-EPIC-09 — Access model / RBAC (IAM service)

New dedicated hexagonal service `src/iam/` (port 8004): users, roles, resources, and role-resource
links. DB RBAC is the Phase-4 fine-grained authorization layer atop Keycloak JWT realm roles.
Cross-links EPIC-03 (Identity & audit), EPIC-07 (Observability), and NLS-104 / NLS-506 (Redis).

**Planner decisions:** D1 dedicated `src/iam/` (not `common/` or `admin_ui/`); D2 ULID string PKs with
prefixes `usr_`/`rol_`/`res_` + `RoleResource` composite PK; D3 extend existing common `UserORM` with a
nullable `role_id` FK → `roles` (ON DELETE SET NULL), no second users table; D4 use `AsyncSession`
(subclass `SqlAlchemyUnitOfWork`); D5 new ORM models live in `common/adapters/database/models/` so
housekeeper Alembic autogenerate sees them.

Ready-made Jira creation script: [`scripts/jira/create_rbac_tasks.ps1`](../../scripts/jira/create_rbac_tasks.ps1)
(supports `-DryRun`). Full titles/context/AC/labels/sizes are authoritative in that script.

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-901 | Add DatabaseException adapter-layer exception | Open | §12 — layered exception model (DatabaseException "future") |
| NLS-902 | db_measure metrics decorator + CrudOperation enum | Open | §12 — observability (x-link NLS-701) |
| NLS-903 | Cursor pagination helper + ext_str util | Open | §12 — shared common utils; PaginatedResponseSchema |
| NLS-904 | IAM service scaffold (src/iam/) | Open | §12 — hexagonal service layout; §5 Phase 4 |
| NLS-905 | RBAC domain entities | Open | §5 Phase 4 — access model; §12 domain layering |
| NLS-906 | AccessModelRepository + AccessModelUnitOfWork ports | Open | §12 — ports & adapters (mirror patients) |
| NLS-907 | RBAC domain commands + queries | Open | §12 — Commands/Queries; backend_conventions |
| NLS-908 | IAM domain/tasks.py orchestration stub | Open | §12 — exception-orchestration rule |
| NLS-909 | RBAC ORM models + extend UserORM | Open | §5 — auth users schema; §12 persistence |
| NLS-910 | Alembic migration 0003_rbac | Open | §4 Housekeeper — centralized Alembic env |
| NLS-911 | SQLAlchemyAccessModelRepository (postgres.py) | Open | §12 — persistence adapters (mirror PostgresUserRepository) |
| NLS-912 | SQLAlchemy IAM Unit of Work | Open | §12 — unit of work (SqlAlchemyUnitOfWork) |
| NLS-913 | Redis cache adapter + wiring | Open | §6 Redis (x-link NLS-104 / NLS-506) |
| NLS-914 | Outbound gateways/ HTTP client scaffold | Open | §12 — outbound gateways (admin_ui httpx pattern) |
| NLS-915 | email/ notification adapter scaffold | Open | §12 — notifier port (paymentgate parity) |
| NLS-916 | IAM HTTP adapter (router, schemas, deps) | Open | §12 — HTTP adapters; ResponseSchema/PaginatedResponseSchema |
| NLS-917 | Fake in-memory access model (repo + UoW) | Open | §12 — in-memory adapters (mirror patients in_mem.py) |
| NLS-918 | Domain unit tests against fakes + conftest | Open | §12 — tests (asyncio_mode=auto) |
| NLS-919 | Smoke test on FakeUnitOfWork (no Postgres) | Open | §12 — smoke tests use FakeUnitOfWork |
| NLS-920 | SQLAlchemy adapter integration tests (marked, Postgres) | Open | §12 — adapter integration tests; CI gates |
| NLS-921 | IAM Docker/compose/Makefile wiring | Open | §12 — per-service Dockerfile + compose + Make |
| NLS-922 | ADR + docs update (id strategy, UserORM, RBAC schema) | Open | §5 / §6 — RBAC as Phase-4 layer atop JWT realm roles |

**Dependency-ordered milestones (M-A → M-E):**

- **M-A Foundations:** NLS-901 → NLS-902, NLS-903, NLS-904
- **M-B Domain:** NLS-905 → NLS-906 → NLS-907, NLS-908; NLS-909
- **M-C Persistence:** NLS-910 → NLS-911 → NLS-912; NLS-917
- **M-D Edges:** NLS-913, NLS-914, NLS-915, NLS-916
- **M-E Tests/ops/docs:** NLS-918, NLS-919, NLS-920, NLS-921, NLS-922

---

## Gateway + browser OIDC (Pioneer extension)

Decomposes M2 for **Sprint 01 — Pioneer**. NeuroAtlas uses **Keycloak JWT directly** at the API edge (no AtomID exchange). Browser flow: **authorization code + PKCE** → gateway BFF holds refresh → forwards **Bearer** to backends.

| Ref | Jira | Epic | Title | Status |
|-----|------|------|-------|--------|
| NLS-GW-01 | NLS-50 | EPIC-01 | Gateway service scaffold (`src/gateway/`, hex layout) | Open |
| NLS-GW-02 | NLS-51 | EPIC-01 | Reverse proxy to patients / ml / housekeeper | Open |
| NLS-GW-03 | NLS-52 | EPIC-03 | Keycloak **browser** client (`neuroatlas-ui`, redirect URIs, CORS) | Done (superseded by NLS-ADMIN-02) |
| NLS-GW-04 | NLS-53 | EPIC-01 | Gateway OIDC routes: `/auth/login`, `/auth/callback`, `/auth/logout` | Open |
| NLS-GW-05 | NLS-54 | EPIC-01 | Session: httpOnly refresh cookie + in-memory access + Bearer forward | Open |
| NLS-GW-06 | NLS-55 | EPIC-02 | E2E smoke: browser login → gateway → patients `/api/v1/patients` + JIT row | Open |
| NLS-GW-07 | NLS-56 | EPIC-08 | Frontend Keycloak browser login (redirect / PKCE or gateway session) | Open |
| NLS-GW-08 | NLS-57 | EPIC-08 | Frontend calls API only via gateway base URL | Open |
| NLS-GW-09 | NLS-58 | EPIC-01 | `application.compose.yml`: gateway on stack (port 8000) | Open |
| NLS-GW-10 | NLS-59 | EPIC-03 | Doc: `auth-browser-gateway-flow.md` sequence diagram | Partial |

**Overlap:** NLS-101..103 and NLS-802..803 remain umbrella stories; close or link when NLS-GW-* are Done.

**Out of Pioneer:** NLS-104 (Redis rate limit), full auth removal from service handlers (optional follow-up).

**Pioneer pivot (admin_ui):** Browser entry is **`admin_ui` BFF** (PaymentGate-style embedded React + auth handlers on port 8000), not standalone `gateway` + Next.js. Stories **NLS-ADMIN-01..09** supersede NLS-GW-* for the browser path; NLS-GW-* remain for traceability until closed or linked.

| Ref | Jira | Epic | Title | Status |
|-----|------|------|-------|--------|
| NLS-ADMIN-01 | NLS-61 | EPIC-01 | `admin_ui` service scaffold (`src/admin_ui/`) | Partial |
| NLS-ADMIN-02 | NLS-62 | EPIC-03 | Keycloak `neuroatlas-ui` client (admin_ui callback) | Done |
| NLS-ADMIN-03 | NLS-63 | EPIC-01 | OIDC auth handlers (token, refresh, logout, `/auth/me`) | Open |
| NLS-ADMIN-04 | NLS-64 | EPIC-01 | Guard proxy `/guard/api/v1/*` → patients / ml | Open |
| NLS-ADMIN-05 | NLS-65 | EPIC-08 | React admin UI (auth pages + patients MVP) | Open |
| NLS-ADMIN-06 | NLS-66 | EPIC-01 | Static SPA serving + `window._env_` | Open |
| NLS-ADMIN-07 | NLS-67 | EPIC-01 | Docker compose: `admin_ui` on port 8000 | Open |
| NLS-ADMIN-08 | NLS-68 | EPIC-02 | E2E smoke: browser login → patients + JIT row | Partial |
| NLS-ADMIN-09 | NLS-69 | EPIC-03 | Auth diagram: admin_ui BFF flow | Done |

Create in Jira: `.\scripts\jira\create_admin_ui_tasks.ps1` (adds to Sprint Pioneer id 35).

---

## Suggested sprint order (first 3 milestones)

### Milestone M1 — Runnable clinical API
- NLS-201, NLS-202, NLS-301, NLS-302

### Milestone M2 — admin_ui BFF + browser auth (Pioneer extension)
- NLS-ADMIN-01 → NLS-ADMIN-02 → NLS-ADMIN-03 → NLS-ADMIN-04 → NLS-ADMIN-06 → NLS-ADMIN-07 → NLS-ADMIN-08
- Parallel when `/auth/me` works: NLS-ADMIN-05 (React UI)
- NLS-ADMIN-09 alongside docs
- Legacy gateway path (NLS-GW-01..10): superseded by NLS-ADMIN-* for browser; keep for audit until linked/closed

### Milestone M3 — Event-driven ML path
- NLS-401, NLS-601, NLS-403

---

## Active sprint

**Sprint 03 — Clinical API foundation** (19 Jul → 2 Aug 2026, Jira sprint id **101**, board name `S03 Clinical API`): see [`sprint-03-clinical-api.md`](sprint-03-clinical-api.md)

**Sprint goal:** Finish admin_ui E2E + auth docs; patients on Postgres.

**Previous:** [Sprint 02 — admin_ui Pioneer](sprint-02-admin-ui-pioneer.md) (id 68, closed) · [Sprint 01 — Pioneer](sprint-01-pioneer.md) (id 35, closed).

Full backlog keys: [`backlog-keys.md`](backlog-keys.md) (67 stories + 9 epics incl. NLS-GW-01..10 and NLS-901..922).

---

## How to use in Jira

See [`docs/jira/README.md`](README.md) for API setup, CLI commands, and the **`scrum_master`** Cursor agent.

Jira key mapping (plan ref to Jira key): [`backlog-keys.md`](backlog-keys.md).

1. Create project **NeuroAtlas** (or your prefix).
2. Create epics `NLS-EPIC-01` … `NLS-EPIC-08`.
3. Create stories from the tables above (copy **Title** as summary, **Ticket** as issue key if allowed).
4. Paste **ARCHITECTURE.md ref** into description + link to §12.
5. Update **Status** column here when tickets move (optional local tracker).
