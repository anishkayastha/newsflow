# NewsFlow

Event-driven news digest system.

NewsFlow ingests 190 RSS feeds, clusters articles by real-world events using Sentence-BERT + DBSCAN, scores clusters by relevance/authority/recency, and generates a single multi-source summary per event using DistilBART.

The result is a ranked, deduplicated news feed served via a serverless API and React frontend with Cognito authentication.

---

## Core Idea

This is not a summarizer.

It is a cluster → score → summarize pipeline:
- Multiple articles about the same event are grouped first
- Then one high-quality summary is generated per event

---

## Architecture

EventBridge (every 12 hours)
    ↓
Lambda: scraper
    → fetch 190 RSS feeds
    → push to SQS (batched)
    ↓
SQS (batch size: 10,000, window: 300s)
    ↓
Lambda: consumer (Docker)
    → SBERT embeddings
    → DBSCAN clustering
    → scoring
    → DistilBART summarization
    → quality gate
    → DynamoDB
    ↓
Lambda: API (plain Python)
    → returns ranked digest
    ↓
API Gateway (HTTP API)
    ↓
React SPA (Vite + Amplify + Cognito)
    ↓
S3 + CloudFront

---

## Project Structure

newsflow/
├── Makefile
├── config.mk.example
│
├── backend/
│   ├── scraper/
│   ├── consumer/
│   ├── api/
│
├── frontend/
└── docs/

---

## Important Architectural Decisions

- Models baked into Docker (no S3 download)
- Plain Python API (no FastAPI)
- Python 3.12 for compatibility
- 12-hour schedule (cost optimization)
- Large SQS batching required for clustering
- Cognito SPA auth (no hosted UI)
- CORS configured at API Gateway + Lambda

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker
- AWS CLI configured

### Setup

git clone <your-repo>
cd newsflow

cp config.mk.example config.mk
cp frontend/.env.example frontend/.env

### Install

make setup

### Deploy Backend

make deploy-backend

### Test

make fresh-run
make logs-consumer

### Deploy Frontend

make deploy-frontend

---

## Key Parameters

- DBSCAN eps: 0.35
- min samples: 2
- scoring: 0.50 relevance / 0.25 authority / 0.25 recency
- summary length: 20–200 words

---

## Performance

- ~3,600 articles processed
- ~260 clusters
- ~95% quality pass rate

---

## Commands

- make deploy-all
- make deploy-backend
- make deploy-frontend
- make fresh-run
- make logs-consumer

---

## Known Limitations

- Duplicate clusters across batches
- Cold start ~2–4 min
- No global deduplication

---

## Planned Improvements

- S3 staging for global clustering
- Step Functions orchestration
- Better deduplication

---

## Cost

~$5–7/month

---

## Status

Backend: working  
API: working  
Frontend: deploying  

---

## License

MIT
