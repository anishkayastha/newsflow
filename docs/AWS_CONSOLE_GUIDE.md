# NewsFlow — AWS Build Guide
### From notebook to live pipeline using AWS Management Console

> **Scope:** Everything except the React frontend.
> Covers: S3 · SQS · DynamoDB · ECR · Lambda (scraper + consumer) · EventBridge · CloudWatch · SNS

---

## Before You Touch AWS — Local Prep (Do This First)

All AWS Console steps depend on having three things ready locally:

1. **`sbert.tar.gz`** and **`distilbart.tar.gz`** — packaged model weights to upload to S3
2. **`scraper.zip`** — packaged scraper Lambda code
3. **A Docker image** of the consumer Lambda pushed to ECR

Do these steps on your machine before opening the AWS console.

### Requirements
- Python 3.11, pip, Docker (running), AWS CLI v2
- ~5 GB free disk, ~8 GB RAM, stable internet (models are large)

---

### Local Step A — Download and package models

```bash
# Create project folder
mkdir newsflow && cd newsflow
mkdir -p models scripts scraper consumer

# Copy the three provided source files into place:
#   scraper/handler.py   → the scraper Lambda code
#   consumer/handler.py  → the consumer Lambda code
#   consumer/Dockerfile  → the container definition
#   consumer/requirements.txt
#   scripts/download_and_package_models.py

# Install download deps
pip install sentence-transformers transformers torch

# Run — takes 5–15 minutes depending on connection speed
python scripts/download_and_package_models.py
```

Expected output:
```
sbert.tar.gz size: ~380 MB
distilbart.tar.gz size: ~290 MB
✅ Done. Upload these two files to S3 ...
```

You now have `models/sbert.tar.gz` and `models/distilbart.tar.gz`.

---

### Local Step B — Package the scraper Lambda zip

```bash
cd scraper
pip install feedparser boto3 -t ./package/
cp handler.py ./package/
cd package && zip -r ../scraper.zip . && cd ..
cd ..
# Result: scraper/scraper.zip (~2 MB)
```

---

### Local Step C — Build and push consumer Docker image to ECR

You need your **AWS Account ID** (12-digit number) for this step.
Find it: AWS Console → top-right account dropdown → copy the 12-digit number.

```bash
export AWS_ACCOUNT_ID=YOUR_12_DIGIT_ACCOUNT_ID
export AWS_REGION=ap-southeast-1   # change to your preferred region

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS \
    --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build the image (takes 10–20 min first time — torch is large)
cd consumer
docker build -t newsflow-consumer .

# Tag and push
docker tag newsflow-consumer:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/newsflow-consumer:latest
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/newsflow-consumer:latest
cd ..
```

> **Note:** ECR repository must exist before pushing. Create it in Step 3 below,
> then come back and run the push commands.

---

## AWS Console Steps

Open https://console.aws.amazon.com — make sure your region (top-right) matches
the region you used in Local Step C.

---

## Step 1 — Create the S3 bucket for model weights

**Service:** S3 → Buckets → Create bucket

| Field | Value |
|---|---|
| Bucket name | `newsflow-models-[your-account-id]` (must be globally unique) |
| AWS Region | Same as your chosen region |
| Object Ownership | ACLs disabled (default) |
| Block all public access | ✅ Enabled (models are private) |
| Versioning | Disabled |
| Encryption | SSE-S3 (default) |

Click **Create bucket**.

### Upload model weights

Open the bucket → **Upload** → **Add files**

Upload both files:
- `models/sbert.tar.gz`
- `models/distilbart.tar.gz`

In the upload dialog, set the **Destination path prefix** to `models/` so they land at:
- `s3://newsflow-models-[account]/models/sbert.tar.gz`
- `s3://newsflow-models-[account]/models/distilbart.tar.gz`

Click **Upload**. This takes several minutes — the files are ~670 MB combined.

> Keep this tab open — you'll need the bucket name for Lambda env vars later.

---

## Step 2 — Create the three DynamoDB tables

**Service:** DynamoDB → Tables → Create table

Create **three tables** with these settings. Repeat for each:

### Table 1: nf-articles

| Field | Value |
|---|---|
| Table name | `nf-articles` |
| Partition key | `id` (String) |
| Sort key | (none) |
| Table settings | Customize |
| Capacity mode | On-demand |
| Encryption | Owned by Amazon DynamoDB |

Click **Create table**.

### Table 2: nf-clusters

| Field | Value |
|---|---|
| Table name | `nf-clusters` |
| Partition key | `cluster_id` (String) |
| Sort key | (none) |
| Capacity mode | On-demand |

### Table 3: nf-summaries

| Field | Value |
|---|---|
| Table name | `nf-summaries` |
| Partition key | `cluster_id` (String) |
| Sort key | (none) |
| Capacity mode | On-demand |

All three tables should reach **Active** status within 30 seconds.

---

## Step 3 — Create the ECR repository

**Service:** ECR (Elastic Container Registry) → Repositories → Create repository

| Field | Value |
|---|---|
| Visibility | Private |
| Repository name | `newsflow-consumer` |
| Tag immutability | Disabled |
| Scan on push | Enabled |
| Encryption | AES-256 |

Click **Create repository**.

After creating, copy the **URI** shown (e.g. `123456789.dkr.ecr.ap-southeast-1.amazonaws.com/newsflow-consumer`).

**Now go back and run Local Step C** (the docker build + push commands) using this URI.

---

## Step 4 — Create the SQS queue

**Service:** SQS → Queues → Create queue

| Field | Value |
|---|---|
| Type | **Standard** (not FIFO — FIFO adds complexity without benefit here) |
| Name | `newsflow-articles` |
| Visibility timeout | `900` seconds (must be ≥ consumer Lambda timeout) |
| Message retention | `1 day` (86,400 seconds) |
| Maximum message size | 256 KB |
| Receive message wait time | `20` seconds (long polling — saves cost) |
| Dead-letter queue | Create new → name `newsflow-articles-dlq`, max receives = 3 |

Click **Create queue**.

After creation, copy the **Queue URL** — looks like:
`https://sqs.ap-southeast-1.amazonaws.com/123456789/newsflow-articles`

You'll paste this into the scraper Lambda env vars.

---

## Step 5 — Create IAM roles for the Lambdas

**Service:** IAM → Roles → Create role

Create **two roles**, one for each Lambda.

### Role 1: newsflow-scraper-role

**Step 1 of wizard:** Trusted entity type = **AWS service** → Use case = **Lambda** → Next

**Step 2:** Attach these policies (search and tick each):
- `AWSLambdaBasicExecutionRole` (for CloudWatch Logs)
- `AmazonSQSFullAccess`
- `CloudWatchFullAccess`

**Step 3:** Role name = `newsflow-scraper-role` → Create role

### Role 2: newsflow-consumer-role

Same process, but attach:
- `AWSLambdaBasicExecutionRole`
- `AmazonSQSFullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonS3ReadOnlyAccess`
- `CloudWatchFullAccess`

Role name = `newsflow-consumer-role` → Create role

---

## Step 6 — Create the Scraper Lambda

**Service:** Lambda → Functions → Create function

| Field | Value |
|---|---|
| Author from scratch | ✅ |
| Function name | `newsflow-scraper` |
| Runtime | Python 3.11 |
| Architecture | x86_64 |
| Execution role | Use existing → `newsflow-scraper-role` |

Click **Create function**.

### Upload the code

On the function page → **Code** tab → **Upload from** → **.zip file**
Upload `scraper/scraper.zip`.

After upload, verify the file browser shows `handler.py`.

### Set the handler

**Runtime settings** → Edit
- Handler: `handler.lambda_handler`

### Set environment variables

**Configuration** tab → **Environment variables** → Edit → Add:

| Key | Value |
|---|---|
| `SQS_QUEUE_URL` | Paste the queue URL from Step 4 |

Save.

### Set timeout and memory

**Configuration** → **General configuration** → Edit:

| Setting | Value |
|---|---|
| Memory | 512 MB |
| Timeout | 5 min 0 sec |

Save.

---

## Step 7 — Create the Consumer Lambda

**Service:** Lambda → Functions → Create function

| Field | Value |
|---|---|
| **Container image** | ✅ (select this option, not "Author from scratch") |
| Function name | `newsflow-consumer` |
| Container image URI | Paste the ECR image URI from Step 3 (with `:latest` tag) |
| Architecture | x86_64 |
| Execution role | Use existing → `newsflow-consumer-role` |

Click **Create function**.

> If the image isn't showing in the picker, paste the URI directly.

### Set environment variables

**Configuration** → **Environment variables** → Edit → Add:

| Key | Value |
|---|---|
| `MODEL_BUCKET` | `newsflow-models-[your-account-id]` |
| `TABLE_ARTICLES` | `nf-articles` |
| `TABLE_CLUSTERS` | `nf-clusters` |
| `TABLE_SUMMARIES` | `nf-summaries` |

Save.

### Set timeout and memory

**Configuration** → **General configuration** → Edit:

| Setting | Value |
|---|---|
| Memory | **3008 MB** (3 GB — needed to hold both models in RAM) |
| Timeout | **15 min 0 sec** (maximum; cold start + full pipeline can take 10–12 min) |
| Ephemeral storage (/tmp) | **2048 MB** (models are extracted here on cold start) |

Save.

### Connect SQS to the consumer Lambda

**Configuration** → **Triggers** → **Add trigger**

| Field | Value |
|---|---|
| Source | SQS |
| SQS queue | `newsflow-articles` |
| Batch size | `100` |
| Batch window | `30` seconds |
| Enabled | ✅ |

Click **Add**.

This tells Lambda to automatically invoke the consumer whenever articles arrive in SQS.

---

## Step 8 — Schedule the scraper with EventBridge

**Service:** EventBridge → Rules → Create rule

| Field | Value |
|---|---|
| Name | `newsflow-scraper-schedule` |
| Event bus | default |
| Rule type | **Schedule** |

Click **Continue to create rule**.

**Schedule pattern:**
- Select **A schedule that runs at a regular rate**
- Rate: `30` minutes

Click **Next**.

**Target:**
- Target types: AWS service
- Select target: **Lambda function**
- Function: `newsflow-scraper`

Click **Next** → **Next** → **Create rule**.

The scraper will now fire automatically every 30 minutes.

---

## Step 9 — Create SNS topic for alerts

**Service:** SNS → Topics → Create topic

| Field | Value |
|---|---|
| Type | Standard |
| Name | `newsflow-alerts` |

Click **Create topic**.

### Subscribe your email

On the topic page → **Subscriptions** → **Create subscription**

| Field | Value |
|---|---|
| Protocol | Email |
| Endpoint | your@email.com |

Click **Create subscription**, then **confirm the email** that arrives in your inbox.

Copy the **Topic ARN** — you'll need it for CloudWatch alarms.

---

## Step 10 — CloudWatch alarms

**Service:** CloudWatch → Alarms → All alarms → Create alarm

Create **two alarms**.

### Alarm 1: Quality gate degradation

**Step 1 — Select metric:**
- Browse → NewsFlow namespace → `QualityGatePassRate`
- Statistic: Average | Period: 30 minutes

**Step 2 — Conditions:**
- Threshold type: Static
- Whenever `QualityGatePassRate` is **Lower than** `0.8`
- Treat missing data as: missing

**Step 3 — Notifications:**
- In alarm → SNS topic → `newsflow-alerts`

**Step 4 — Name:** `NewsFlow-LowQualityGate`

Create alarm.

### Alarm 2: Pipeline dead (no articles ingested)

**Step 1 — Select metric:**
- Browse → NewsFlow namespace → `ArticlesIngested`
- Statistic: Sum | Period: 60 minutes

**Step 2 — Conditions:**
- Whenever `ArticlesIngested` is **Lower than** `1`
- Treat missing data as: **breaching**

**Step 3 — Notifications:**
- In alarm → `newsflow-alerts`

**Step 4 — Name:** `NewsFlow-NoArticles`

Create alarm.

> **Note:** The `NewsFlow` metric namespace won't appear in the picker until the scraper
> Lambda has run at least once and published metrics. Run Step 11 first if it's missing.

---

## Step 11 — Test the pipeline manually

Before waiting 30 minutes for the EventBridge schedule, trigger the scraper manually.

**Service:** Lambda → Functions → `newsflow-scraper` → **Test** tab

Create a test event:
- Event name: `manual-trigger`
- Event JSON: `{}`

Click **Test**.

Watch the **Execution results** panel. Expected:
```
{"status": "ok", "articles": 1847, "feeds_ok": 156}
```

Numbers will vary — some feeds may be temporarily down.

### Monitor the consumer

After the scraper runs, articles flow into SQS, which triggers the consumer.
The consumer takes **8–12 minutes** on cold start (model download + model load + inference).

Check progress: Lambda → `newsflow-consumer` → **Monitor** tab → **View CloudWatch logs**

You'll see:
```
[COLD START] downloading sbert from s3://...
[COLD START] downloading distilbart from s3://...
[INFO] Models loaded and cached
[OK] 1847 articles → 312 clusters → 289 summaries passed | sil=0.451 | qg=0.924
```

---

## Step 12 — CloudWatch dashboard

**Service:** CloudWatch → Dashboards → Create dashboard

Name: `NewsFlow-Pipeline`

Add widgets (click **Add widget** for each):

### Widget 1 — Articles ingested
- Type: Line
- Metric: NewsFlow → `ArticlesIngested`, Sum, 30 min

### Widget 2 — Quality gate pass rate
- Type: Line
- Metric: NewsFlow → `QualityGatePassRate`, Average, 30 min

### Widget 3 — Clusters formed
- Type: Line
- Metric: NewsFlow → `ClustersFormed`, Sum, 30 min

### Widget 4 — DistilBART latency
- Type: Line
- Metric: NewsFlow → `MeanDistilBARTLatency`, Average, 30 min

### Widget 5 — Silhouette score
- Type: Line
- Metric: NewsFlow → `SilhouetteScore`, Average, 30 min

### Widget 6 — Feeds active
- Type: Number (single value)
- Metric: NewsFlow → `FeedsActive`, Maximum, 30 min

Save dashboard.

---

## Step 13 — Verify data in DynamoDB

**Service:** DynamoDB → Tables → `nf-summaries` → **Explore table items**

After the consumer runs, you should see items with fields like:
```json
{
  "cluster_id": "cluster_5_20260413143022",
  "summary": "Artemis II crew successfully departs Kennedy Space Center...",
  "score": "0.8124",
  "topic": "Science",
  "article_count": 45,
  "passed_gate": true
}
```

Sort by `score` descending to see the top-ranked events — this is your digest.

---

## Deployment Checklist

```
[ ] models/sbert.tar.gz uploaded to s3://newsflow-models-[account]/models/
[ ] models/distilbart.tar.gz uploaded to s3://newsflow-models-[account]/models/
[ ] DynamoDB tables: nf-articles, nf-clusters, nf-summaries — all Active
[ ] SQS queue: newsflow-articles — Standard, 900s visibility, 20s long-poll
[ ] ECR repository: newsflow-consumer — image tagged :latest pushed
[ ] scraper Lambda: Python 3.11, 512 MB, 5 min timeout, SQS_QUEUE_URL env set
[ ] consumer Lambda: container image, 3008 MB, 15 min timeout, 2048 MB /tmp, all 4 env vars set
[ ] consumer Lambda trigger: SQS newsflow-articles, batch 100, window 30s
[ ] EventBridge rule: newsflow-scraper-schedule, rate(30 minutes), target scraper Lambda
[ ] SNS topic: newsflow-alerts, email subscription confirmed
[ ] CloudWatch alarm: NewsFlow-LowQualityGate (< 0.8)
[ ] CloudWatch alarm: NewsFlow-NoArticles (< 1 per hour)
[ ] CloudWatch dashboard: NewsFlow-Pipeline with 6 widgets
[ ] Manual test: scraper returns articles_ok, consumer log shows clusters formed
[ ] DynamoDB nf-summaries: items visible with passed_gate = true
```

---

## Cost Reference

All services stay within free tier at demo scale:

| Service | Usage | Cost |
|---|---|---|
| S3 | ~720 MB model storage | ~$0.02/month |
| SQS | ~50k messages/day | Free tier |
| DynamoDB | < 25 GB | Free tier |
| Lambda scraper | ~1,440 invocations/month (every 30 min) | Free tier |
| Lambda consumer | ~1,440 invocations × 10 min avg × 3 GB | ~$1.69/month |
| CloudWatch | 6 custom metrics | Free tier |
| SNS | < 1,000 emails/month | Free tier |
| ECR | ~2 GB image storage | ~$0.20/month |
| **Total** | | **~$2/month** |

---

## Troubleshooting

**Consumer Lambda times out on first run**
The 15-minute timeout covers model download + load + inference. If it times out, check
S3 download speed from your region. You can pre-warm by invoking with a small test batch.

**SQS messages not triggering the consumer**
Verify the trigger is Enabled in the consumer Lambda's Configuration → Triggers tab.
Also confirm the consumer role has `AmazonSQSFullAccess`.

**CloudWatch metrics namespace doesn't appear**
The `NewsFlow` namespace is auto-created on first `put_metric_data` call. Run the scraper
manually (Step 11) then wait 2 minutes for metrics to propagate.

**DynamoDB items missing after consumer runs**
Check CloudWatch Logs for the consumer. If you see `AccessDeniedException`, the consumer role
is missing `AmazonDynamoDBFullAccess`. Add the policy in IAM → Roles → newsflow-consumer-role.

**feedparser returns 0 articles from a feed**
Some feeds block requests without a User-Agent. The handler already sends
`User-Agent: NewsFlow/1.0` — if a specific feed still fails, check it with:
`curl -A "NewsFlow/1.0" https://the-feed-url`

**Docker build fails on arm Mac (M1/M2/M3)**
Add `--platform linux/amd64` to the docker build command:
`docker build --platform linux/amd64 -t newsflow-consumer .`
