# Sprint 01 — Pioneer

**Milestone:** M1 — Runnable clinical API  
**Sprint goal:** Postgres-backed patients service with Keycloak auth and JIT user upsert on the production request path.

**Status:** **Active** in Jira (project key `NLS`) — sprint **Pioneer** (id 35).

> **Sprint vs backlog:** This sprint has **4 stories** (NLS-14 … 17). The 8 **epics** (NLS-6 … 13) live on the **Backlog** — they are not sprint tasks. On the board, use the sprint selector and pick **Pioneer**.

### Sprint issues (what you should see on the board)

| # | plan.md | Jira key | Summary |
|---|---------|----------|---------|
| 1 | NLS-301 | NLS-14 | Keycloak realm bootstrap |
| 2 | NLS-202 | NLS-15 | Alembic migrations |
| 3 | NLS-201 | NLS-16 | Patients SQLAlchemy adapter |
| 4 | NLS-302 | NLS-17 | JIT user upsert |

Verify in terminal:

```powershell
.\scripts\jira\jira_api.ps1 sprint-issues 35
```

### Full backlog key mapping (epics + stories)

| plan.md ref | Jira key | URL |
|-------------|----------|-----|
| NLS-EPIC-01 | NLS-6 | https://neurojihad.atlassian.net/browse/NLS-6 |
| NLS-EPIC-02 | NLS-7 | https://neurojihad.atlassian.net/browse/NLS-7 |
| NLS-EPIC-03 | NLS-8 | https://neurojihad.atlassian.net/browse/NLS-8 |
| NLS-EPIC-04 | NLS-9 | https://neurojihad.atlassian.net/browse/NLS-9 |
| NLS-EPIC-05 | NLS-10 | https://neurojihad.atlassian.net/browse/NLS-10 |
| NLS-EPIC-06 | NLS-11 | https://neurojihad.atlassian.net/browse/NLS-11 |
| NLS-EPIC-07 | NLS-12 | https://neurojihad.atlassian.net/browse/NLS-12 |
| NLS-EPIC-08 | NLS-13 | https://neurojihad.atlassian.net/browse/NLS-13 |
| NLS-301 | NLS-14 | https://neurojihad.atlassian.net/browse/NLS-14 |
| NLS-202 | NLS-15 | https://neurojihad.atlassian.net/browse/NLS-15 |
| NLS-201 | NLS-16 | https://neurojihad.atlassian.net/browse/NLS-16 |
| NLS-302 | NLS-17 | https://neurojihad.atlassian.net/browse/NLS-17 |

---

## Sprint backlog (dependency order)

| # | Ref | Summary | Epic | Status in repo | Depends on |
|---|-----|---------|------|----------------|------------|
| 1 | NLS-301 | Keycloak realm bootstrap (`neuroatlas`, roles, client) | NLS-EPIC-03 | Open | — |
| 2 | NLS-202 | Alembic migrations: patients + assessments tables | NLS-EPIC-02 | Open | — |
| 3 | NLS-201 | Patients SQLAlchemy adapter (replace in-memory UoW) | NLS-EPIC-02 | Partial | NLS-202 (schema) |
| 4 | NLS-302 | Shadow `users` table JIT upsert in production path | NLS-EPIC-03 | Partial | NLS-301 (realm) |

### Out of scope for Pioneer

- ML Kafka path (M3)
- Patient-level ACL (NLS-204)
- Integration tests against Postgres (NLS-203) — stretch if capacity allows
- Rate limiting (NLS-104) — post-Pioneer

### Pioneer extension — gateway + browser Keycloak auth

Add these from backlog to **Pioneer** manually (dependency order):

| # | Jira | Ref | Summary | Epic | Depends on |
|---|------|-----|---------|------|------------|
| 5 | NLS-50 | NLS-GW-01 | Gateway service scaffold (embed pattern) | NLS-6 | — |
| 6 | NLS-52 | NLS-GW-03 | Keycloak browser client (redirect URIs, CORS) | NLS-8 | NLS-14 |
| 7 | NLS-51 | NLS-GW-02 | Gateway reverse proxy to backends | NLS-6 | NLS-50 |
| 8 | NLS-53 | NLS-GW-04 | Gateway OIDC login/callback/logout | NLS-6 | NLS-52, NLS-50 |
| 9 | NLS-54 | NLS-GW-05 | Session cookie + Bearer forwarding | NLS-6 | NLS-53 |
| 10 | NLS-55 | NLS-GW-06 | Patients auth smoke via gateway | NLS-7 | NLS-54, NLS-17 |
| 11 | NLS-56 | NLS-GW-07 | Frontend Keycloak browser login | NLS-13 | NLS-53 |
| 12 | NLS-57 | NLS-GW-08 | Frontend API via gateway | NLS-13 | NLS-51, NLS-56 |
| 13 | NLS-58 | NLS-GW-09 | Docker compose gateway on stack | NLS-6 | NLS-51 |
| 14 | NLS-59 | NLS-GW-10 | Auth diagram: gateway + browser flow | NLS-8 | — |

**Existing backlog overlap:** NLS-18 (embed gateway), NLS-19..21 (plan NLS-101..103), NLS-48..49 (plan NLS-802..803). New tasks decompose the browser auth path; close or link duplicates when done.

**Original M2 gateway items** (NLS-19, 20, 21) remain on backlog for full consolidation — Pioneer extension uses embed scaffold first (NLS-GW-01).

---

## Epics to create (full backlog)

| Ref | Epic title |
|-----|------------|
| NLS-EPIC-01 | Microservice foundation |
| NLS-EPIC-02 | Clinical data (Patients) |
| NLS-EPIC-03 | Identity & audit |
| NLS-EPIC-04 | Event backbone |
| NLS-EPIC-05 | Knowledge base (RAG pipeline) |
| NLS-EPIC-06 | Machine learning |
| NLS-EPIC-07 | Observability & ops |
| NLS-EPIC-08 | Frontend |

Source: [`plan.md`](plan.md)

---

## Definition of Done (sprint)

- [ ] `make up_infra` brings Keycloak with `neuroatlas` realm ready
- [ ] Patients + assessments tables exist via Alembic / housekeeper
- [ ] Patients service persists to Postgres (SQLAlchemy UoW)
- [ ] JIT user upsert active when `USER_UPSERT_ENABLED=true`
- [ ] Browser login via Keycloak through gateway reaches patients API (NLS-55)
- [ ] `make test_patients` green; manual smoke against Postgres documented

---

## Bootstrap in Jira

After setup (see [`README.md`](README.md#setup)):

```powershell
.\scripts\jira\jira_api.ps1 verify
.\scripts\jira\bootstrap_pioneer.ps1
```

This creates all 8 epics, 4 M1 stories, sprint **Pioneer**, and assigns stories to the sprint.

---

## Recommended next agent

When Pioneer stories exist in Jira, invoke **`planner`** then **`implementer`** starting with **NLS-301** or **NLS-202** (can run in parallel).
