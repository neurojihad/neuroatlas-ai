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

### 3.1 Web App (Frontend)
- **Stack:** Next.js (App Router), React, TypeScript, Tailwind, TanStack Query.
- **Responsibilities:** assessment entry forms, prediction + SHAP visualization
  (waterfall/force plots), evidence panel with citations, session history.
- **Auth:** OIDC (e.g. Auth0/Keycloak); role-based (clinician, researcher, admin).

### 3.2 API Gateway (Backend)
- **Stack:** FastAPI + Pydantic v2, Uvicorn/Gunicorn.
- **Responsibilities:** request validation, authn/z, rate limiting, audit
  logging, request fan-out/orchestration, response assembly.
- **Cross-cutting:** structured logging, OpenTelemetry tracing, error envelope.

### 3.3 ML Service
- **Stack:** Python, scikit-learn, **XGBoost** (baseline), **SHAP** (explainability).
- **Endpoints:** `POST /predict` → `{outcome, probability, shap_values}`.
- **Models:** outcome prediction, rehab-progress trajectory, risk stratification.
- **Lifecycle:** training pipeline (offline) → model registry → served as artifact.
- **Targets (examples):** GMFCS level change, MACS change, goal attainment.

### 3.4 RAG Service
- **Stack:** Python, sentence-transformers / BGE embeddings, vector DB.
- **Endpoints:** `POST /search` → ranked passages + source metadata.
- **Pipeline:** ingest → clean → chunk → embed → index; query → retrieve →
  re-rank (cross-encoder) → return with provenance.

### 3.5 LLM Orchestrator
- **Stack:** LangChain or LlamaIndex; provider-agnostic adapter
  (OpenAI / Anthropic / local vLLM).
- **Responsibilities:** prompt templating, context assembly (ML + RAG),
  citation enforcement, guardrails (refuse out-of-scope/clinical-directive asks).
- **Pattern:** retrieval-grounded generation with **mandatory inline citations**;
  no claim without a source.

### 3.6 Ingestion Pipelines
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

## 6. Proposed Repository Structure

```
neuroatlas-ai/
├── README.md
├── ARCHITECTURE.md
├── docker-compose.yml
├── apps/
│   └── web/                  # Next.js frontend
├── services/
│   ├── gateway/              # FastAPI API gateway
│   ├── ml/                   # training + serving (XGBoost/SHAP)
│   ├── rag/                  # retrieval service
│   └── llm/                  # LLM orchestrator
├── pipelines/
│   ├── ingestion/            # PubMed/guideline ingestion
│   └── training/             # ML training DAGs
├── packages/
│   └── schemas/              # shared Pydantic/TS types (contracts)
├── data/                     # DVC-tracked (gitignored payloads)
├── notebooks/                # research & EDA
├── infra/                    # IaC, k8s manifests, CI/CD
└── docs/                     # ADRs, data dictionary, model cards
```

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

| Phase | Architectural slice to build |
|-------|------------------------------|
| **1 — Research** | Data dictionary, ADRs, dataset datasheets in `docs/` |
| **2 — RAG MVP** | Ingestion pipeline + RAG service + pgvector + LLM cite-only |
| **3 — ML MVP** | ML service: XGBoost baseline + SHAP + MLflow registry |
| **4 — Unified** | Gateway orchestration + Next.js web app + full deployment |

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

*Next step suggestion:* scaffold the repository structure in section 6 with
runnable skeletons (FastAPI gateway, RAG service, docker-compose) so Phase 2 can
start immediately.
```
