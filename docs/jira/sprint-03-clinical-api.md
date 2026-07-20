# Sprint 03 — Clinical API foundation

**Dates:** 19 Jul 2026 → 2 Aug 2026 (2 weeks)  
**Jira name:** `S03 Clinical API` (30-char limit) — sprint id **101**  
**Sprint goal:** Finish admin_ui E2E + auth docs; patients on Postgres.

**Status:** **Active** in Jira (project key `NLS`).

**Previous:** [Sprint 02 — admin_ui Pioneer](sprint-02-admin-ui-pioneer.md) (id 68, closed).

---

## Context

Sprint 02 delivered the **admin_ui** BFF path (NLS-61..67 Done). Sprint 03 closes the pioneer loop
(E2E smoke + auth diagram) and starts **Milestone M1** — a runnable clinical API backed by Postgres
instead of in-memory storage.

Superseded **gateway** stories (NLS-50..59) were moved back to the backlog; link or close them
against NLS-ADMIN-* equivalents when convenient.

---

## Sprint backlog

| # | plan ref | Jira | Summary | Epic | Depends on | Status |
|---|----------|------|---------|------|------------|--------|
| 1 | NLS-ADMIN-08 | NLS-68 | E2E smoke: browser login via admin_ui → patients + JIT | NLS-7 | NLS-63, NLS-17 | In Progress |
| 2 | NLS-ADMIN-09 | NLS-69 | Auth diagram: admin_ui BFF + browser OIDC flow | NLS-8 | — | Done |
| 3 | NLS-202 | NLS-15 | Alembic migrations: patients + assessments tables | NLS-7 | — | To Do |
| 4 | NLS-201 | NLS-16 | Patients SQLAlchemy adapter (replace in-memory UoW) | NLS-7 | NLS-15 | To Do |
| 5 | NLS-203 | NLS-25 | Patients integration tests against Postgres | NLS-7 | NLS-15, NLS-16 | To Do |

Verify sprint membership:

```powershell
.\scripts\jira\jira_api.ps1 sprint-issues 101
```

---

## Definition of Done (sprint)

- [ ] `make smoke_admin_ui` passes with `AUTH_ENABLED=true` (NLS-68)
- [x] Auth diagram updated for admin_ui BFF flow (NLS-69)
- [ ] Patients + assessments tables migrated; SQLAlchemy UoW replaces in-memory (NLS-15, NLS-16)
- [ ] Integration tests run against Postgres (NLS-25)
- [ ] `make check` green on touched packages
- [ ] Sprint stories moved to Done in Jira; `plan.md` statuses updated

---

## Recommended agent order

1. **NLS-68** — finish E2E smoke ([`docs/smoke/admin-ui-e2e.md`](../smoke/admin-ui-e2e.md))
2. **NLS-15 → NLS-16 → NLS-25** — Postgres persistence path (M1)
3. Parallel: **NLS-69** — auth diagram ([`auth-admin-ui-browser-flow.md`](../diagrams/auth-admin-ui-browser-flow.md))

Delegate implementation to **`implementer`** with Jira key + acceptance criteria from [`plan.md`](plan.md).

---

## Jira notes

- Sprint names on this board are limited to **30 characters**.
- To move issues out of a sprint: `POST /rest/agile/1.0/backlog/issue` (see scrum_master agent).
- Gateway carry-over (NLS-50..59) remains in backlog for link/close against NLS-ADMIN-*.
