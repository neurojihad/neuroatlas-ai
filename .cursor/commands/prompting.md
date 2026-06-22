# NeuroAtlas AI — Project Context

NeuroAtlas AI is a research-oriented clinical decision support platform for pediatric neurorehabilitation.

The initial focus is:

* Pediatric hemiparesis
* Hemiplegic cerebral palsy (unilateral cerebral palsy)
* Pediatric neurorehabilitation

The long-term vision is to help clinicians quickly access scientific evidence and, in the future, support outcome prediction using machine learning.

## Current MVP Goal

The first version of NeuroAtlas AI is NOT a diagnostic system and NOT a treatment recommendation system.

The MVP is an evidence retrieval assistant built using RAG (Retrieval-Augmented Generation).

Its purpose is to help clinicians and researchers find relevant scientific evidence from medical literature.

## User Scenario

A clinician asks:

"What rehabilitation approaches have demonstrated benefits in children with hemiplegic cerebral palsy?"

The system should:

1. Search indexed scientific literature.
2. Retrieve the most relevant publications.
3. Extract relevant evidence.
4. Provide a concise answer.
5. Cite the sources used.

The response must always be grounded in retrieved literature.

The model should never invent evidence.

## Knowledge Sources

The primary knowledge source is PubMed.

The platform should be designed so that additional sources can be added later:

* Clinical guidelines
* Research registries
* Rehabilitation protocols
* Institutional knowledge bases

## Architecture Principles

The system should follow a modular architecture.

Core modules:

### Literature Ingestion

Responsible for:

* Retrieving articles from PubMed
* Parsing metadata
* Storing scientific content

### Document Processing

Responsible for:

* Text cleaning
* Chunking
* Metadata preservation

### Embedding Pipeline

Responsible for:

* Generating vector embeddings
* Storing embeddings
* Updating embeddings

### Retrieval Layer

Responsible for:

* Semantic search
* Similarity ranking
* Context retrieval

### RAG Layer

Responsible for:

* Retrieving relevant chunks
* Building context
* Interacting with the LLM

### API Layer

Responsible for:

* User requests
* Search endpoints
* Response formatting

## MVP Features

The MVP should support:

* PubMed article ingestion
* Article chunking
* Embedding generation
* Vector storage using pgvector
* Semantic search
* Retrieval-Augmented Generation (RAG)
* Evidence-based answers
* Source citations

## Technology Stack

Backend:

* Python 3.12
* FastAPI
* PostgreSQL 17
* pgvector
* SQLAlchemy 2.0
* Alembic

AI:

* OpenAI API
* LlamaIndex
* Sentence Transformers

Infrastructure:

* Docker
* Docker Compose

Quality:

* Ruff
* MyPy
* Pytest

## Development Principles

Follow:

* Clean Architecture
* SOLID
* Repository Pattern
* Service Layer Pattern
* Dependency Injection
* Strong Typing
* Async First

Avoid:

* Business logic inside routers
* Global state
* Tight coupling
* Monolithic services

## Future Roadmap

The platform will later include a Machine Learning module.

The ML module is NOT part of the MVP.

Future ML goals:

* Functional outcome prediction
* Rehabilitation outcome estimation
* Explainable predictions using SHAP
* Clinical feature analysis

Potential features:

* Age
* GMFCS
* MACS
* Ashworth
* Goniometry
* Therapy type

Potential targets:

* Functional improvement
* MACS improvement
* GMFCS improvement
* Reduction in spasticity

## Development Strategy

Implement incrementally.

Priority order:

1. Project infrastructure
2. PostgreSQL + pgvector
3. PubMed ingestion
4. Chunking pipeline
5. Embedding pipeline
6. Retrieval layer
7. RAG service
8. FastAPI endpoints
9. Basic UI
10. ML module (future)

After each phase:

* Explain architecture decisions
* Explain tradeoffs
* Keep code production-ready
* Add tests where appropriate

The codebase should remain modular, maintainable, and suitable for future healthcare AI research and development.
