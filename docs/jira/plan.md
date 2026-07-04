# NeuroAtlas — Jira Backlog Plan

Ticket names for creating epics/stories in Jira. Keys (`NLS-xxx`) are **suggested** — adjust to your
project prefix. Link each ticket to [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §12 for context.

**Status key:** `Open` = not started · `Partial` = scaffold exists · `Done` = complete (update as you track)

---

## Epic: NLS-EPIC-01 — Microservice foundation

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-101 | API Gateway service (FastAPI entry point) | Open | §12, §5 Phase 2 |
| NLS-102 | Gateway routing to patients / ml / housekeeper | Open | §4 Gateway |
| NLS-103 | Centralize OIDC auth at gateway | Open | §5 Phase 2 |
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
| NLS-301 | Keycloak realm bootstrap (`neuroatlas`, roles, client) | Open | §5, §6 Keycloak |
| NLS-302 | Shadow `users` table JIT upsert in production path | Partial | §5, `docs/diagrams/` |
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

---

## Epic: NLS-EPIC-08 — Frontend

| Ticket | Title | Status | ARCHITECTURE.md ref |
|--------|-------|--------|---------------------|
| NLS-801 | Next.js app scaffold | Open | §10 Phase 5 |
| NLS-802 | Keycloak login flow in UI | Open | §5 |
| NLS-803 | Gateway integration from UI | Open | §10 Phase 5 |

---

## Suggested sprint order (first 3 milestones)

### Milestone M1 — Runnable clinical API
- NLS-201, NLS-202, NLS-301, NLS-302

### Milestone M2 — Gateway + auth consolidation
- NLS-101, NLS-102, NLS-103

### Milestone M3 — Event-driven ML path
- NLS-401, NLS-601, NLS-403

---

## Active sprint

**Sprint 01 — Pioneer** (M1, Jira sprint id 35): see [`sprint-01-pioneer.md`](sprint-01-pioneer.md)

Full backlog keys: [`backlog-keys.md`](backlog-keys.md) (35 stories + 8 epics).

---

## How to use in Jira

See [`docs/jira/README.md`](README.md) for API setup, CLI commands, and the **`scrum_master`** Cursor agent.

Jira key mapping (plan ref to Jira key): [`backlog-keys.md`](backlog-keys.md).

1. Create project **NeuroAtlas** (or your prefix).
2. Create epics `NLS-EPIC-01` … `NLS-EPIC-08`.
3. Create stories from the tables above (copy **Title** as summary, **Ticket** as issue key if allowed).
4. Paste **ARCHITECTURE.md ref** into description + link to §12.
5. Update **Status** column here when tickets move (optional local tracker).
