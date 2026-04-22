# NewsFlow

Event-driven news digest system. Ingests 190 RSS feeds every 30 minutes,
clusters articles by event using Sentence-BERT + DBSCAN, scores each cluster
by relevance/authority/recency, and generates one multi-source summary per
event using DistilBART. Served as a ranked digest via React + Cognito auth.

---

## Project structure

```
newsflow/
├── Makefile                    ← all terminal commands live here
├── config.mk.example           ← copy to config.mk and fill in your AWS values
├── .gitignore
│
├── backend/
│   ├── scraper/
│   │   ├── handler.py          ← Lambda: fetches 190 RSS feeds → SQS
│   │   └── requirements.txt
│   │
│   ├── consumer/
│   │   ├── handler.py          ← Lambda: embed → cluster → score → summarize → DynamoDB
│   │   ├── Dockerfile          ← container image (needed for ML deps)
│   │   └── requirements.txt
│   │
│   ├── api/
│   │   ├── handler.py          ← Lambda: FastAPI serving digest from DynamoDB
│   │   └── requirements.txt
│   │
│   └── scripts/
│       └── download_and_package_models.py  ← run once locally before deploying
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example            ← copy to .env and fill in Cognito + API values
│   └── src/
│       ├── main.jsx            ← Amplify.configure + ReactDOM.createRoot
│       ├── App.jsx             ← Cognito Authenticator wrapper
│       ├── config.js           ← reads VITE_* env vars
│       ├── index.css           ← design tokens + global styles
│       ├── hooks/useDigest.js  ← fetch + auto-refresh every 30 min
│       ├── utils/time.js       ← timeAgo(), topicClass()
│       ├── components/
│       │   ├── Header.jsx
│       │   ├── CategoryFilter.jsx
│       │   ├── DigestCard.jsx
│       │   └── LoadingSkeleton.jsx
│       └── pages/
│           └── DigestPage.jsx  ← main page
│
└── docs/
    └── AWS_CONSOLE_GUIDE.md    ← step-by-step AWS Console setup (13 steps)
```

---

## Quick start

### Step 0 — Prerequisites
- Python 3.11, Node.js 18+, Docker (running), AWS CLI v2 configured
- `aws configure` done with your IAM credentials

### Step 1 — Clone and configure

```bash
git clone <your-repo-url> newsflow
cd newsflow

# Backend config
cp config.mk.example config.mk
# Open config.mk and fill in your AWS account ID, region, bucket names

# Frontend config
cp frontend/.env.example frontend/.env
# Open frontend/.env and fill in Cognito + API Gateway values
```

### Step 2 — Install dependencies

```bash
make setup
```

### Step 3 — Download ML models (one-time, ~700 MB)

```bash
make download-models
# Produces: backend/models/sbert.tar.gz + backend/models/distilbart.tar.gz
```

### Step 4 — Set up AWS infrastructure (Console)

Follow `docs/AWS_CONSOLE_GUIDE.md` steps 1–9:
- S3 model bucket → upload the two .tar.gz files (`make upload-models`)
- DynamoDB tables (nf-articles, nf-clusters, nf-summaries)
- ECR repository
- SQS queue
- IAM roles
- Lambda functions (scraper, consumer, api)
- EventBridge schedule
- SNS + CloudWatch alarms

### Step 5 — Deploy backend

```bash
# First time — build everything from scratch
make upload-models        # push model weights to S3
make deploy-consumer      # build Docker image → push ECR → update Lambda
make deploy-scraper       # zip → update Lambda
make deploy-api           # zip → update Lambda

# All subsequent code changes — one command
make deploy-backend
```

### Step 6 — Test the pipeline

```bash
make test-scraper         # invoke scraper manually + print result
make logs-consumer        # tail consumer CloudWatch logs (watch it run)
make logs-api             # tail API logs
```

### Step 7 — Deploy frontend

```bash
# Fill in frontend/.env first (Cognito + API Gateway URL)
make deploy-frontend      # build → S3 sync → CloudFront invalidation
```

---

## Day-to-day commands

| Task | Command |
|---|---|
| Deploy everything after code changes | `make deploy-all` |
| Deploy backend only | `make deploy-backend` |
| Deploy frontend only | `make deploy-frontend` |
| Trigger scraper manually | `make test-scraper` |
| Watch consumer logs live | `make logs-consumer` |
| Run frontend locally | `cd frontend && npm run dev` |
| Clean build artifacts | `make clean` |

---

## AWS services used

| Service | Role | Monthly cost |
|---|---|---|
| EventBridge | Triggers scraper every 30 min | $0 |
| Lambda — scraper | Fetches 190 RSS feeds | $0 |
| SQS | Article buffer between Lambdas | $0 |
| Lambda — consumer | SBERT + DBSCAN + DistilBART | ~$3–5 |
| Lambda — api | FastAPI digest endpoint | $0 |
| S3 (models) | Stores 720 MB model weights | ~$0.02 |
| S3 (frontend) | Hosts React build | ~$0 |
| DynamoDB | Clusters + summaries storage | $0 |
| ECR | Consumer Docker image | ~$0.40 |
| CloudWatch + SNS | Metrics, alarms, email alerts | $0 |
| Cognito | User auth (JWT) | $0 |
| API Gateway | HTTP API endpoint | $0 |
| CloudFront | CDN for React SPA | $0 |
| **Total** | | **~$5–7 / month** |

---

## Key pipeline parameters (from `backend/consumer/handler.py`)

| Parameter | Value | Effect |
|---|---|---|
| `DBSCAN_EPS` | 0.35 | Articles with cosine distance > 0.35 are not grouped |
| `DBSCAN_MIN_SAMPLES` | 2 | Minimum articles to form a cluster |
| Scoring weights | 0.50 relevance + 0.25 authority + 0.25 recency | Cluster importance |
| Quality gate min words | 20 | Summaries shorter than this are rejected |
| Quality gate max words | 200 | Summaries longer than this are rejected |
| SBERT model | all-mpnet-base-v2 | 768-dim embeddings, ~420 MB |
| Summarizer | sshleifer/distilbart-cnn-6-6 | ~300 MB, CPU-safe |
