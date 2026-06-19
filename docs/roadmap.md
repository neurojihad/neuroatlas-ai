# NeuroAtlas AI Roadmap

## Vision

NeuroAtlas AI is a Clinical Decision Support System for Pediatric Neurorehabilitation.

The platform combines:

* Retrieval-Augmented Generation (RAG)
* Large Language Models (LLMs)
* Machine Learning (ML)

to assist clinicians in understanding evidence, analyzing patient data, and evaluating rehabilitation outcomes.

---

# Phase 0 — Research

## Goals

Understand:

* Pediatric hemiparesis
* Unilateral cerebral palsy
* Neurorehabilitation workflows
* Clinical outcome measures
* Existing datasets

## Tasks

### Literature Review

Study:

* Hemiplegic Cerebral Palsy
* Pediatric Hemiparesis
* CIMT
* Bimanual Therapy
* Pediatric Neurorehabilitation

### Clinical Scales

Understand:

* GMFCS
* MACS
* Ashworth Scale
* AHA
* Goniometry

### Dataset Discovery

Investigate:

* CP registries
* Rehabilitation datasets
* Longitudinal studies
* Open-access databases

### Expert Outreach

Contact:

* Researchers
* Clinicians
* Universities
* Rehabilitation centers

## Deliverables

* Research notes
* Dataset inventory
* Clinical workflow documentation

---

# Phase 1 — RAG MVP

## Goal

Build a scientific evidence retrieval system.

## Features

### PubMed Integration

Collect:

* Research papers
* Reviews
* Clinical studies

### Ingestion Pipeline

Pipeline:

PubMed
→ Parser
→ Chunking
→ Embeddings
→ Vector Database

### Embeddings

Evaluate:

* BGE
* OpenAI Embeddings
* Sentence Transformers

### Vector Database

Use:

* PostgreSQL
* pgvector

### Retrieval

Support:

* Semantic search
* Similarity search
* Evidence retrieval

### LLM Layer

Generate:

* Research summaries
* Evidence-based answers
* References

## Deliverables

Working RAG system capable of answering questions using PubMed literature.

---

# Phase 2 — Backend Platform

## Goal

Build production-ready backend services.

## Stack

* Python
* FastAPI
* PostgreSQL
* pgvector
* Docker

## Modules

### Auth

* User management
* Roles

### Research API

Endpoints:

* Search
* Retrieval
* Evidence generation

### Clinical API

Store:

* Assessments
* Functional scores
* Clinical notes

## Deliverables

Backend API for NeuroAtlas.

---

# Phase 3 — ML Foundations

## Goal

Build first predictive models.

## Learn

### Scikit-Learn

* Classification
* Regression
* Evaluation metrics

### XGBoost

Train models for:

* Outcome prediction
* Risk estimation

### SHAP

Explain:

* Feature importance
* Model predictions

## Deliverables

Baseline predictive models.

---

# Phase 4 — Clinical Prediction MVP

## Goal

Predict rehabilitation outcomes.

## Inputs

Examples:

* Age
* GMFCS
* MACS
* Ashworth
* Goniometry
* Therapy type

## Outputs

Examples:

* Probability of improvement
* Risk factors
* Expected outcomes

## Explainability

Provide:

* SHAP explanations
* Human-readable interpretation

## Deliverables

Clinical prediction prototype.

---

# Phase 5 — Unified AI Assistant

## Goal

Combine all AI components.

## Architecture

Clinical Data
→ ML

Scientific Literature
→ RAG

ML + RAG
→ LLM

LLM
→ Clinician Assistant

## Features

* Evidence retrieval
* Outcome prediction
* Risk explanation
* Literature navigation

## Deliverables

NeuroAtlas AI Assistant.

---

# Long-Term Vision

NeuroAtlas becomes an evidence-driven platform for:

* Pediatric neurorehabilitation
* Clinical decision support
* Rehabilitation outcome prediction
* Research assistance

---

# Current Focus

Current milestone:

Research
→ PubMed Integration
→ RAG MVP

ML development begins after acquiring sufficient longitudinal clinical data.
