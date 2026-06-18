# NeuroAtlas AI — System Architecture

> Status: **Draft v0.1** — research-phase architecture for a Clinical Decision
> Support System (CDSS) in pediatric neurorehabilitation.
>
> ⚠️ **Research only.** Not a medical device. Not for diagnosis or treatment
> decisions. See [Compliance & Safety](#8-compliance-safety--ethics).

---

## 1. Overview

NeuroAtlas AI helps clinicians in **pediatric neurorehabilitation** (initial
focus: **cerebral palsy, CP**) by combining three capabilities behind one API:

1. **ML** — predict functional outcomes & rehabilitation progress from
   structured assessments.
2. **RAG** — retrieve relevant scientific evidence (PubMed, guidelines).
3. **LLM** — generate plain-language, evidence-grounded explanations.

The guiding principle is **"prediction + evidence + explanation, never a black
box."** Every model output is paired with feature attributions (SHAP) and every
narrative claim is paired with a citation.

### 1.1 Design goals

| Goal | Implication |
|------|-------------|
| Clinician trust | Explainability (SHAP) + citations are mandatory, not optional |
| Reproducibility | Versioned data, models, prompts, and evidence snapshots |
| Privacy-first | PII/PHI de-identified at the edge; models never see raw identifiers |
| Modularity | ML, RAG, and LLM are independent, separately deployable services |
| Incremental delivery | Ship RAG → ML → unified platform (matches README roadmap) |

---

## 2. High-Level Architecture

```
                         ┌──────────────────────────────┐
                         │        Web App (UI)          │
                         │  Next.js / React + TS        │
                         └───────────────┬──────────────┘
                                         │ HTTPS / JSON
                         ┌───────────────▼──────────────┐
                         │      API Gateway (FastAPI)   │
                         │  authn/z · validation · audit│
                         └───┬───────────┬───────────┬──┘
                             │           │           │
              ┌──────────────▼─┐   ┌─────▼──────┐  ┌─▼───────────────┐
              │  ML Service    │   │ RAG Service│  │  LLM Orchestrator│
              │  XGBoost+SHAP  │   │ retrieval  │  │  (LangChain/     │
              │  /predict      │   │ /search    │  │   LlamaIndex)    │
              └──────┬─────────┘   └─────┬──────┘  └─────┬───────────┘
                     │                   │               │
        ┌────────────▼───┐   ┌───────────▼──────┐  ┌─────▼─────────┐
        │ Feature Store /│   │ Vector DB        │  │  LLM Provider │
        │ Postgres       │   │ (pgvector/Qdrant)│  │  (OpenAI/local│
        │ (clinical data)│   │ + metadata store │  │   vLLM)       │
        └────────────────┘   └───────────▲──────┘  └───────────────┘
                                         │
                              ┌──────────┴───────────┐
                              │ Ingestion Pipelines  │
                              │ PubMed · guidelines  │
                              │ (chunk · embed · idx)│
                              └──────────────────────┘
```

**Request flow (typical "explain this patient" call):**

1. UI sends a de-identified patient assessment to the API gateway.
2. Gateway validates, authorizes, and writes an audit record.
3. ML service returns a prediction + SHAP attributions.
4. RAG service retrieves top-k evidence for the salient features/diagnosis.
5. LLM orchestrator composes a grounded explanation citing (3) and (4).
6. Gateway returns `{prediction, attributions, explanation, citations}`.

---

## 3. Components

### 3.1 Web App (Frontend) — *planned*
- **Stack:** Next.js (App Router), React, TypeScript, Tailwind, TanStack Query.
- **Responsibilities:** assessment entry forms, prediction + SHAP visualization
  (waterfall/force plots), evidence panel with citations, session history.
- **Auth:** OIDC (e.g. Auth0/Keycloak); role-based (clinician, researcher, admin).

### 3.2 API Gateway (Backend) — *planned*
- **Stack:** FastAPI + Pydantic v2, Uvicorn/Gunicorn.
- **Responsibilities:** request validation, authn/z, rate limiting, audit
  logging, request fan-out/orchestration, response assembly.
- **Cross-cutting:** structured logging, OpenTelemetry tracing, error envelope.

### 3.3 Patients Service (Clinical Data) — *implemented*
- **Stack:** FastAPI + Pydantic; hexagonal layers (see §6.1).
- **Endpoints:** `POST /api/v1/patients`, `GET /api/v1/patients[/{id}]`,
  `POST|GET /api/v1/patients/{id}/assessments`.
- **Domain:** `Patient` (surrogate id, birth *year* only), `Assessment`
  (GMFCS, MACS, Modified Ashworth, ROM, clinical note) with scale validation.
- **Persistence:** in-memory adapter today (runs with zero infra); Postgres
  (SQLAlchemy) adapter behind the same ports is the next step.

### 3.4 ML Service — *implemented (baseline)*
- **Stack:** Python, FastAPI. Trained models will use **XGBoost** + **SHAP**;
  the scaffold ships a transparent linear baseline behind an `OutcomePredictor`
  port so the predict→attribute contract is exercisable without native wheels.
- **Endpoints:** `POST /api/v1/predict` → `{target, probability, label,
  model_version, baseline, attributions[]}`.
- **Explainability:** every response carries SHAP-style per-feature
  attributions + the model baseline (exact for the linear baseline; identical
  contract once XGBoost+SHAP lands).
- **Targets (examples):** GMFCS level improvement, goal attainment.
- **Lifecycle:** training pipeline (offline) → model registry → loaded into the
  predictor adapter; domain/HTTP untouched on model swap.

### 3.5 RAG Service — *planned*
- **Stack:** Python, sentence-transformers / BGE embeddings, vector DB.
- **Endpoints:** `POST /search` → ranked passages + source metadata.
- **Pipeline:** ingest → clean → chunk → embed → index; query → retrieve →
  re-rank (cross-encoder) → return with provenance.

### 3.6 LLM Orchestrator — *planned*
- **Stack:** LangChain or LlamaIndex; provider-agnostic adapter
  (OpenAI / Anthropic / local vLLM).
- **Responsibilities:** prompt templating, context assembly (ML + RAG),
  citation enforcement, guardrails (refuse out-of-scope/clinical-directive asks).
- **Pattern:** retrieval-grounded generation with **mandatory inline citations**;
  no claim without a source.

### 3.7 Ingestion Pipelines — *planned*
- PubMed E-utilities + guideline PDFs → parse → de-dup → chunk → embed → upsert.
- Scheduled (Airflow/Prefect or cron) with snapshot versioning for reproducibility.

---

## 4. Data Architecture

### 4.1 Clinical data model (structured)
Core entities (de-identified):

- `patient` (surrogate id only, no PII), `encounter`, `assessment`
- Assessment types: **GMFCS**, **MACS**, **Modified Ashworth**, **ROM**,
  clinical notes (free text), imaging metadata/links.
- `prediction`, `explanation`, `evidence_citation`, `audit_log`.

**Store:** PostgreSQL (relational + JSONB for flexible assessment payloads).

### 4.2 Evidence data (unstructured)
- Vector DB: **pgvector** (start simple, same DB) or **Qdrant** (scale-out).
- Each chunk carries: source, PMID/DOI, title, year, section, license, hash.

### 4.3 Versioning & reproducibility
- **Data:** DVC or LakeFS for datasets; immutable evidence snapshots.
- **Models:** MLflow model registry (params, metrics, artifacts, lineage).
- **Prompts:** version-controlled prompt templates with semantic version tags.

---

## 5. Tech Stack Summary

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Next.js + TS + Tailwind | Fast, typed, good DX, SSR for auth |
| Backend | FastAPI + Pydantic | Async, typed, great for ML serving |
| ML | XGBoost + SHAP + scikit-learn | Strong tabular baseline + explainability |
| Embeddings | BGE / sentence-transformers | Open, strong retrieval quality |
| Vector DB | pgvector → Qdrant | Start in Postgres, scale later |
| LLM | Provider-agnostic (OpenAI/vLLM) | Avoid lock-in; local option for privacy |
| Orchestration | LangChain / LlamaIndex | Mature RAG primitives |
| Relational DB | PostgreSQL | JSONB flexibility + reliability |
| Experiment tracking | MLflow | Registry + reproducibility |
| Pipelines | Prefect / Airflow | Scheduled ingestion + training |
| Infra | Docker + Compose → K8s | Local parity, cloud scale |
| Observability | OpenTelemetry + Prometheus/Grafana | Tracing + metrics |

---

## 6. Repository Structure

A single Poetry monorepo with a `src/<service>/` layout and per-service
dependency groups (pattern adapted from the `paymentgate` service). `✓` = in the
repo today, `▢` = planned.

```
neuroatlas-ai/
├── README.md
├── ARCHITECTURE.md
├── pyproject.toml            # ✓ Poetry, per-service dep groups, ruff/mypy/pytest
├── Makefile                  # ✓ run/lint/test/fmt targets
├── docker-compose.yml        # ✓ postgres(pgvector) + patients + ml
├── infra/
│   └── .env.example          # ✓ local config template
└── src/
    ├── common/               # ✓ app factory, settings, logging,
    │                         #   core ports (Command, UnitOfWork), http schemas
    ├── patients/             # ✓ clinical data service (hexagonal)
    ├── ml/                   # ✓ outcome prediction service (hexagonal)
    ├── rag/                  # ▢ retrieval service (same skeleton)
    ├── llm/                  # ▢ LLM orchestrator (same skeleton)
    ├── gateway/              # ▢ API gateway / orchestrator
    └── housekeeper/          # ▢ Alembic migrations (centralized)
```

Future additions matching §2: `apps/web/` (Next.js), `pipelines/`
(ingestion + training), `notebooks/`, `docs/` (ADRs, data dictionary, model
cards), and DVC-tracked `data/` / `models/` (gitignored payloads).

### 6.1 Service internal architecture (hexagonal / ports & adapters)

Every service follows the same layering so the domain never depends on
frameworks or I/O:

```
src/<service>/
├── main.py                   # FastAPI app built via common app factory
├── settings.py               # dataclass Settings subclass
├── lifespan.py               # startup/shutdown, wires adapters into app.state
├── Dockerfile
├── domain/                   # pure business logic (no FastAPI / DB imports)
│   ├── entities.py           # dataclasses / enums
│   ├── commands.py           # writes: Command + frozen Context + execute()
│   ├── queries.py            # reads
│   ├── exceptions.py
│   └── ports/                # abstract interfaces the domain depends on
│       ├── repositories.py   #   (patients) persistence ports
│       ├── uow.py            #   UnitOfWork transactional boundary
│       └── predictor.py      #   (ml) model port
├── adapters/                 # concrete implementations of the ports
│   ├── database/             # in_mem.py now; postgres.py (SQLAlchemy) next
│   ├── predictor/            # (ml) baseline.py; xgboost.py later
│   └── http/                 # handlers.py (routers), schemas.py, dependencies.py
└── tests/                    # test_domain/, test_adapters/
```

**Conventions carried over from paymentgate:**
- **Command pattern** — each write is a `Command` with a frozen `Context`;
  `validate_context()` runs on construction, business logic in `execute()`.
- **Unit of Work** — `async with uow:` commits on success / rolls back on error;
  the concrete UoW lives in `adapters/database`.
- **Dependency rule** — `domain` imports only `domain` + `common.core`; adapters
  depend on the domain, never the reverse. Swapping in Postgres or XGBoost
  touches only `adapters/`.
- **Response envelope** — `ResponseSchema` / `ListResponseSchema` and a uniform
  error handler from `common.http`.

---

## 7. Deployment & Environments

- **Local:** `docker-compose` (Postgres+pgvector, services, web) for full parity.
- **Staging/Prod:** Kubernetes; horizontal scaling per service; secrets via
  vault; LLM keys never in images.
- **CI/CD:** lint + type-check + tests + model eval gates before deploy.
- **Three environments:** `dev` / `staging` / `prod` with synthetic data in
  non-prod (no real patient data outside a controlled, approved environment).

---

## 8. Compliance, Safety & Ethics

This handles **pediatric health data** — treat compliance as a first-class
architectural concern, not an afterthought.

- **De-identification at the edge:** no direct identifiers ever reach ML/LLM
  services; use surrogate IDs. Free-text notes pass a PHI-scrubbing step.
- **Regulatory posture:** design toward GDPR / (where applicable) HIPAA-style
  controls; document a data-processing basis; obtain IRB/ethics approval before
  any real-patient data use.
- **Data residency & local LLM option:** support self-hosted LLM (vLLM) so PHI
  need not leave the trust boundary.
- **Auditability:** every prediction/explanation is logged with model version,
  evidence snapshot, and prompt version.
- **Human-in-the-loop:** outputs are decision *support*; the clinician decides.
  UI must show uncertainty and the "research, not diagnosis" disclaimer.
- **Bias & validation:** track subgroup performance; publish **model cards** and
  **dataset datasheets** in `docs/`.

---

## 9. Mapping to the README Roadmap

| Phase | Architectural slice to build | Status |
|-------|------------------------------|--------|
| **0 — Scaffold** | Monorepo + hexagonal `common`/`patients`/`ml` (in-mem), tooling | ✓ done |
| **1 — Research** | Data dictionary, ADRs, dataset datasheets in `docs/` | ▢ |
| **2 — RAG MVP** | Ingestion pipeline + RAG service + pgvector + LLM cite-only | ▢ |
| **3 — ML MVP** | ML service: XGBoost + SHAP + MLflow registry (replace baseline) | partial (baseline ✓) |
| **4 — Unified** | Gateway orchestration + Next.js web app + full deployment | ▢ |

---

## 10. Open Questions / Decisions to Confirm

These likely came up in the ChatGPT discussion — please confirm so the design
can be finalized:

1. **Datasets** — which CP/neurorehab datasets are realistically obtainable
   (public vs. partner clinic)? This drives the ML feature schema.
2. **LLM hosting** — cloud API (faster) vs. self-hosted (privacy). Default here
   is provider-agnostic with a local option.
3. **Prediction targets** — exact outcomes to predict (GMFCS change horizon,
   goal attainment scaling, spasticity progression?).
4. **Deployment context** — research sandbox only, or pilot inside a clinic?
5. **Vector DB** — stay on pgvector or commit to Qdrant from the start?
6. **Regulatory scope** — target jurisdiction(s) for compliance design.

---

*Next step suggestions:* (1) add the Postgres SQLAlchemy adapter + Alembic
migrations for `patients` behind the existing ports; (2) scaffold `rag` and
`llm` services on the same hexagonal skeleton; (3) add the `gateway`
orchestrator. The domain and HTTP layers stay untouched as adapters are filled in.
