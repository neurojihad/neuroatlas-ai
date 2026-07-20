# NeuroAtlas — Jira Operations

Jira board: **[neurojihad.atlassian.net](https://neurojihad.atlassian.net)** · project **neuroatlas** (key `NLS`).

| Doc | Purpose |
|-----|---------|
| [`plan.md`](plan.md) | Local backlog catalog — epics, stories, milestone order |
| [`backlog-keys.md`](backlog-keys.md) | plan.md ref (`NLS-*`) to Jira key (`NLS-*`) mapping |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) §12 | Microservice alignment — paste refs into ticket descriptions |

Use the **`scrum_master`** Cursor agent (`.cursor/agents/scrum_master.md`) for sprint planning, backlog grooming, and creating issues.

---

## Setup

### 1. API token

1. Open [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Create a token and copy it (shown once).

### 2. Environment variables

Add to `infra/.env` (never commit tokens):

```env
JIRA_BASE_URL=https://neurojihad.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=NLS
```

`infra/.env.example` lists the same keys with empty values.

### 3. Verify connection

**Windows (PowerShell):**

```powershell
.\scripts\jira\jira_api.ps1 verify
.\scripts\jira\jira_api.ps1 search "project = NLS"
.\scripts\jira\jira_api.ps1 boards
```

`verify` checks API token auth and that `JIRA_PROJECT_KEY` exists.

**Bootstrap Sprint Pioneer** (after verify succeeds):

```powershell
.\scripts\jira\bootstrap_pioneer.ps1
.\scripts\jira\bootstrap_backlog.ps1
```

See [`sprint-01-pioneer.md`](sprint-01-pioneer.md).

**Git Bash / Linux / macOS:**

```bash
bash scripts/jira/jira_api.sh search "project = NLS"
bash scripts/jira/jira_api.sh boards
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` on `verify` | Regenerate API token; paste the **full** token into `infra/.env` |
| `Project NLS: not found` | Create **NeuroAtlas** project with key `NLS` in Jira |
| `permission to create issues` | Grant **Create issues** on the project |
| No scrum board | **Boards → Create board → Scrum** for project NLS |

---

## Issue conventions

### Epics

| Key | Title |
|-----|-------|
| NLS-EPIC-01 | Microservice foundation |
| NLS-EPIC-02 | Clinical data (Patients) |
| NLS-EPIC-03 | Identity & audit |
| NLS-EPIC-04 | Event backbone |
| NLS-EPIC-05 | Knowledge base (RAG pipeline) |
| NLS-EPIC-06 | Machine learning |
| NLS-EPIC-07 | Observability & ops |
| NLS-EPIC-08 | Frontend |

Create epics in Jira first if they do not exist. Story keys in `plan.md` are **suggested** — Jira may auto-assign different keys.

### Issue types

| Type | Use for |
|------|---------|
| Epic | Large initiative (tables in plan.md) |
| Story | Feature work with acceptance criteria |
| Task | Ops, docs, CI, one-off chores |

### Description template

```markdown
## Context
<why this work exists>

## Architecture reference
docs/ARCHITECTURE.md §<section> — <one-line summary>

## Acceptance criteria
- [ ] ...
- [ ] ...

## Out of scope
- ...
```

### Labels

`backend` · `ml` · `infra` · `frontend` · `rag` · `auth` · `gateway`

### Status mapping (plan.md ↔ Jira)

| plan.md | Typical Jira status |
|---------|---------------------|
| Open | To Do / Backlog |
| Partial | In Progress (note remaining work in description) |
| Done | Done |

---

## CLI reference

### Search

```powershell
.\scripts\jira\jira_api.ps1 search "project = NLS AND status != Done ORDER BY rank"
```

### Get issue

```powershell
.\scripts\jira\jira_api.ps1 get NLS-201
```

### Create story

```powershell
.\scripts\jira\jira_api.ps1 create `
  -Type Story `
  -Summary "Patients SQLAlchemy adapter (replace in-memory UoW)" `
  -Epic NLS-EPIC-02 `
  -Description "ARCHITECTURE.md §12. Replace in-memory UoW with SQLAlchemy adapter."
```

Bash equivalent:

```bash
bash scripts/jira/jira_api.sh create \
  --type Story \
  --summary "Patients SQLAlchemy adapter (replace in-memory UoW)" \
  --epic NLS-EPIC-02 \
  --description "ARCHITECTURE.md §12."
```

### Comment

```powershell
.\scripts\jira\jira_api.ps1 comment NLS-201 -Description "Grooming: split migration from adapter wiring."
```

### Boards and sprints

```powershell
.\scripts\jira\jira_api.ps1 boards
.\scripts\jira\jira_api.ps1 sprints -BoardId 1
```

### Transitions

```powershell
.\scripts\jira\jira_api.ps1 transitions NLS-201
```

---

## Sprint milestones (first 3)

| Milestone | Stories |
|-----------|---------|
| **M1** — Runnable clinical API | NLS-201, NLS-202, NLS-301, NLS-302 |
| **M2** — Gateway + auth consolidation | NLS-101, NLS-102, NLS-103 |
| **M3** — Event-driven ML path | NLS-401, NLS-601, NLS-403 |

Invoke the `scrum_master` agent to propose a sprint goal, order dependencies, and create/move issues after you confirm the draft.

**Active sprint:** [Sprint 03 — Clinical API foundation](sprint-03-clinical-api.md) (Jira id **101**). Sprint names are limited to **30 characters** on the board.

---

## Epic link note

The create scripts link stories to epics via the `parent` field. If your Jira project uses a different epic-link field (company-managed classic), set the epic manually in the UI or extend the script with `JIRA_EPIC_LINK_FIELD` once you know the custom field ID.

---

## Keeping plan.md in sync

After creating or closing issues in Jira, update the **Status** column in [`plan.md`](plan.md). The `scrum_master` agent does this when it creates tickets on your behalf.
