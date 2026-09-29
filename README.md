# AI Automation Portfolio

> Three production-grade automation systems for lead generation, customer support, and document processing.
> Python 3.11 · n8n · Docker · pytest — every project runs end to end on your machine in under two minutes, offline, with no API keys and no cost.

---

## Overview

Each project in this repository solves a real, expensive, repetitive business problem: qualifying inbound leads, answering first-line support tickets, and keying invoice data by hand. They are built the way production systems are built — separated ingestion / processing / output layers, error handling at every stage, structured logging, a test suite, and a deployment guide.

**77 tests across the three projects.** Every number quoted in a README was produced by running the pipeline against the sample data committed here.

| Project | What it does | Verified run |
|---|---|---|
| **[1 — Lead Generation + Outreach](project-1-lead-generation/)** | Enriches raw B2B leads, scores them 1–10 with an explainable weighted model, writes a personalized outreach email per qualified lead, and disqualifies poor-fit accounts. | 53 leads loaded · 14 hot / 36 warm / 3 disqualified · 35 tests |
| **[2 — RAG Support Chatbot](project-2-support-chatbot-rag/)** | Ingests a product knowledge base into a vector store and answers questions from the actual docs, with source citations and a confidence gate that escalates instead of guessing. | 20 KB docs · 0/8 out-of-KB questions answered (hard gate) · 21 tests |
| **[3 — Document Processing & Invoicing](project-3-document-processing/)** | Extracts structured fields from PDF invoices and inbound emails, classifies and validates each one, persists to a queryable registry, and routes anything questionable to human review. | 10 documents · 8 reported / 2 needs review / 0 failed · 21 tests |

---

## How the AI layer works

Every project ships with a **deterministic reference backend** behind a pluggable interface, so the demo runs completely offline — no API key, no account, no spend, no cold start. That is a deliberate design choice, and it is the same boundary you would use in production to keep an LLM out of your test suite:

- **Project 1** scores leads with an explainable weighted model rather than a black box, so every score carries a written reason a sales rep can argue with.
- **Project 2** is a real RAG pipeline — chunking, hashed TF-IDF embeddings with persisted IDF, ChromaDB retrieval, a tuned confidence threshold — and answers are composed strictly from retrieved context.
- **Project 3** defines a `DocumentExtractor` interface with a regex implementation as the default. Swapping in a Claude-backed extractor is a single class, documented in the project README.

**Stack:** Python 3.11 · n8n (self-hosted) · Docker + docker-compose · PostgreSQL · ChromaDB · pypdf · reportlab · pytest · loguru

---

## Engineering standards

Every project ships with all of the following — no exceptions:

- **Tests** — pytest, happy path plus edge and error cases per module, including tests that run against the real sample data the README describes, not hand-built fixtures
- **Error handling** — try/except with graceful degradation at each stage; a malformed record is routed, never allowed to kill the batch
- **Structured logging** — loguru, INFO for flow events, ERROR for exceptions
- **Clean architecture** — separated ingestion / processing / output layers
- **Architecture diagram** — Mermaid diagram in each project README
- **Deployment guide** — step-by-step `DEPLOYMENT.md` per project
- **Synthetic data only** — every company, contact, document and dollar figure is fictional

---

## Repository Structure

```
ai-automation-portfolio/
│
├── project-1-lead-generation/        # Lead scoring + outreach automation
│   ├── src/                          # enrichment · scoring · outreach · pipeline
│   ├── tests/
│   ├── data/sample_leads.csv         # 54 synthetic B2B leads (1 malformed)
│   ├── n8n/workflow.json
│   ├── Dockerfile · docker-compose.yml · requirements.txt
│   ├── DEPLOYMENT.md
│   └── README.md
│
├── project-2-support-chatbot-rag/    # RAG-powered support agent
│   ├── src/                          # ingestion · embeddings · retrieval · agent · api
│   ├── tests/
│   ├── data/knowledge_base/          # 20 synthetic product docs
│   ├── n8n/workflow.json
│   ├── Dockerfile · docker-compose.yml · requirements.txt
│   ├── DEPLOYMENT.md
│   └── README.md
│
├── project-3-document-processing/    # Invoice + document extraction
│   ├── src/                          # extractor · classifier · registry · reports · pipeline
│   ├── tests/
│   ├── data/incoming/                # 4 real PDFs + 6 simulated emails
│   ├── n8n/workflow.json
│   ├── Dockerfile · docker-compose.yml · requirements.txt
│   ├── DEPLOYMENT.md
│   └── README.md
│
├── shared/requirements-base.txt      # Shared Python dependencies
├── docker-compose.yml                # Base stack: n8n + PostgreSQL
├── .env.example                      # Required environment variables
└── README.md                         # This file
```

---

## Quickstart

**Prerequisites:** Docker Desktop (or Docker Engine + Compose plugin) and Git.

```bash
git clone https://github.com/Hakiller777/ai-automation-portfolio.git
```

Each project is self-contained and has its own quickstart in its README. To run one:

```bash
cd ai-automation-portfolio/project-1-lead-generation
docker compose up --build
```

To run the full n8n + PostgreSQL base stack from the repository root:

```bash
cp .env.example .env
docker compose up -d
```

This starts **n8n** at `http://localhost:5678` and **PostgreSQL** on port `5432`. Import a project's workflow from n8n via **Workflows → Import from file**, selecting `n8n/workflow.json` inside the project folder.

To run a test suite:

```bash
cd project-1-lead-generation
pip install -r requirements.txt
pytest tests/ -v
```

---

## Deployment

Each project includes a step-by-step `DEPLOYMENT.md` for Railway (primary) and Render (fallback). The short version:

1. Create a Railway project and link this repository, setting **Root Directory** to the project folder
2. Add a PostgreSQL service from the Railway marketplace
3. Set the environment variables from `.env.example`
4. Railway detects the `Dockerfile` and builds automatically
5. Import the n8n workflow JSON after the first successful deploy

---

## License

MIT — free to use as reference or template. All business data in this repository is synthetic and fictional.
