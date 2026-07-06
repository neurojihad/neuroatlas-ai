# NeuroAtlas - Jira backlog key mapping

Project key: **NLS**. Plan refs (NLS-*) map to auto-assigned Jira keys.

## Epics

| plan.md | Jira | Title |
|---------|------|-------|
| NLS-EPIC-01 | NLS-6 | Microservice foundation |
| NLS-EPIC-02 | NLS-7 | Clinical data (Patients) |
| NLS-EPIC-03 | NLS-8 | Identity & audit |
| NLS-EPIC-04 | NLS-9 | Event backbone |
| NLS-EPIC-05 | NLS-10 | Knowledge base (RAG pipeline) |
| NLS-EPIC-06 | NLS-11 | Machine learning |
| NLS-EPIC-07 | NLS-12 | Observability & ops |
| NLS-EPIC-08 | NLS-13 | Frontend |

## Stories

| plan.md | Jira | Epic | Title |
|---------|------|------|-------|
| NLS-101 | NLS-19 | EPIC-01 | API Gateway service (FastAPI entry point) |
| NLS-102 | NLS-20 | EPIC-01 | Gateway routing to patients / ml / housekeeper |
| NLS-103 | NLS-21 | EPIC-01 | Centralize OIDC auth at gateway |
| NLS-104 | NLS-22 | EPIC-01 | Rate limiting at gateway (Redis-backed) |
| NLS-105 | NLS-23 | EPIC-01 | Per-service Docker deploy targets in CI |
| NLS-106 | NLS-24 | EPIC-01 | Database-per-service strategy (design + ADR) |
| NLS-201 | NLS-16 | EPIC-02 | Patients SQLAlchemy adapter |
| NLS-202 | NLS-15 | EPIC-02 | Alembic migrations |
| NLS-203 | NLS-25 | EPIC-02 | Patients integration tests against Postgres |
| NLS-204 | NLS-26 | EPIC-02 | Patient-level ACL |
| NLS-301 | NLS-14 | EPIC-03 | Keycloak realm bootstrap |
| NLS-302 | NLS-17 | EPIC-03 | JIT user upsert |
| NLS-303 | NLS-27 | EPIC-03 | Audit events table |
| NLS-304 | NLS-28 | EPIC-03 | Service accounts for ML |
| NLS-401 | NLS-29 | EPIC-04 | Kafka topic bootstrap in CI |
| NLS-402 | NLS-30 | EPIC-04 | Transactional outbox |
| NLS-403 | NLS-31 | EPIC-04 | Saga design |
| NLS-404 | NLS-32 | EPIC-04 | Dead-letter / retry policy |
| NLS-501 | NLS-33 | EPIC-05 | PubMed ingestion |
| NLS-502 | NLS-34 | EPIC-05 | Article storage + chunking |
| NLS-503 | NLS-35 | EPIC-05 | Embedding service |
| NLS-504 | NLS-36 | EPIC-05 | Search service (pgvector) |
| NLS-505 | NLS-37 | EPIC-05 | LLM Orchestrator RAG |
| NLS-506 | NLS-38 | EPIC-05 | Redis cache search/LLM |
| NLS-601 | NLS-39 | EPIC-06 | ML Kafka consumer hardening |
| NLS-602 | NLS-40 | EPIC-06 | XGBoost production adapter |
| NLS-603 | NLS-41 | EPIC-06 | SHAP explainability |
| NLS-604 | NLS-42 | EPIC-06 | Clinical feature store schema |
| NLS-701 | NLS-43 | EPIC-07 | Prometheus metrics |
| NLS-702 | NLS-44 | EPIC-07 | OpenTelemetry tracing |
| NLS-703 | NLS-45 | EPIC-07 | Housekeeper long-query monitoring |
| NLS-704 | NLS-46 | EPIC-07 | Structured audit log export |
| NLS-705 | NLS-71 | EPIC-07 | Self-hosted GitLab Runner (docker executor, project-locked) |
| NLS-801 | NLS-47 | EPIC-08 | Next.js scaffold |
| NLS-802 | NLS-48 | EPIC-08 | Keycloak login UI |
| NLS-803 | NLS-49 | EPIC-08 | Gateway UI integration |

## Gateway + browser auth (Pioneer extension)

| plan ref | Jira | Epic | Title |
|----------|------|------|-------|
| NLS-GW-01 | NLS-50 | NLS-6 | Gateway service scaffold (embed pattern, src/gateway/) |
| NLS-GW-02 | NLS-51 | NLS-6 | Gateway reverse proxy to patients, ml, housekeeper |
| NLS-GW-03 | NLS-52 | NLS-8 | Keycloak browser client: redirect URIs, CORS, neuroatlas-ui |
| NLS-GW-04 | NLS-53 | NLS-6 | Gateway OIDC routes: login, callback, logout (browser) |
| NLS-GW-05 | NLS-54 | NLS-6 | Gateway session cookie and Bearer forwarding to backends |
| NLS-GW-06 | NLS-55 | NLS-7 | Patients API auth smoke via gateway with real Keycloak JWT |
| NLS-GW-07 | NLS-56 | NLS-13 | Frontend Keycloak browser login (OIDC redirect / PKCE) |
| NLS-GW-08 | NLS-57 | NLS-13 | Frontend API integration through gateway entry point |
| NLS-GW-09 | NLS-58 | NLS-6 | Docker compose: gateway service on application stack |
| NLS-GW-10 | NLS-59 | NLS-8 | Auth diagram: gateway + browser OIDC flow |

## admin_ui BFF + React panel (Pioneer - supersedes gateway-only browser path)

| plan ref | Jira | Epic | Title |
|----------|------|------|-------|
| NLS-ADMIN-01 | NLS-61 | NLS-6 | admin_ui service scaffold (src/admin_ui/, hex layout) |
| NLS-ADMIN-02 | NLS-62 | NLS-8 | Keycloak browser client neuroatlas-ui (redirect URIs, admin_ui callback) |
| NLS-ADMIN-03 | NLS-63 | NLS-6 | admin_ui OIDC auth handlers (login, token, refresh, logout, /auth/me) |
| NLS-ADMIN-04 | NLS-64 | NLS-6 | admin_ui guard proxy to patients and ml (/guard/api/v1/*) |
| NLS-ADMIN-05 | NLS-65 | NLS-13 | React admin UI: auth pages, AuthProvider, patients MVP |
| NLS-ADMIN-06 | NLS-66 | NLS-6 | admin_ui static SPA serving (frontend router + window._env_) |
| NLS-ADMIN-07 | NLS-67 | NLS-6 | Docker compose: admin_ui on port 8000 (browser entry) |
| NLS-ADMIN-08 | NLS-68 | NLS-7 | E2E smoke: browser login via admin_ui to patients API + JIT user row |
| NLS-ADMIN-09 | NLS-69 | NLS-8 | Auth diagram: admin_ui BFF + browser OIDC flow |
