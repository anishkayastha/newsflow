# NewsFlow Frontend

React SPA for the NewsFlow event-driven news digest system.
Built with Vite + React + AWS Amplify (Cognito auth).

## Project structure

```
src/
  main.jsx              — entry point, configures Amplify
  App.jsx               — Authenticator wrapper
  config.js             — AWS config (reads from .env)
  index.css             — design tokens + global styles
  utils/time.js         — timeAgo(), topicClass()
  hooks/useDigest.js    — fetches digest with JWT, auto-refreshes every 30 min
  components/
    Header.jsx          — top bar: logo, stats, user, sign out
    CategoryFilter.jsx  — 8-category pill filter
    DigestCard.jsx      — single event card (summary + score + sources)
    LoadingSkeleton.jsx — shimmer placeholders while loading
  pages/
    DigestPage.jsx      — main page, wires all components
```

## Setup

### 1. Install dependencies
```bash
npm install
```

### 2. Configure environment
```bash
cp .env.example .env
```

Open `.env` and fill in your values from the AWS Console:

| Variable | Where to find it |
|---|---|
| `VITE_AWS_REGION` | Region you deployed to (e.g. `ap-southeast-1`) |
| `VITE_USER_POOL_ID` | Cognito → User pools → your pool → Pool ID |
| `VITE_USER_POOL_CLIENT_ID` | Cognito → User pools → your pool → App clients → Client ID |
| `VITE_API_URL` | API Gateway → your API → Stages → Invoke URL (no trailing slash) |

### 3. Run locally
```bash
npm run dev
```
Opens at http://localhost:5173 — Amplify Authenticator shows a login screen.
Create an account with any email (Cognito sends a verification code).

## Build and deploy

### 1. Build
```bash
npm run build
```
Produces `dist/` — static HTML, JS, CSS files ready for S3.

### 2. Configure deploy.sh
Open `deploy.sh` and set `S3_BUCKET`, `CLOUDFRONT_ID`, and `AWS_REGION`.

### 3. Deploy
```bash
chmod +x deploy.sh
./deploy.sh
```

This uploads the build to S3, sets correct cache headers
(`index.html` is never cached; assets are cached permanently by content hash),
then invalidates the CloudFront distribution so users get the new version immediately.

## What the API returns

The `useDigest` hook calls `GET {API_URL}/digest?limit=200`.

Expected response from the FastAPI Lambda:
```json
{
  "digest": [
    {
      "cluster_id":    "cluster_5_20260413143022",
      "summary":       "Artemis II leaves Earth's orbit...",
      "score":         "0.8124",
      "relevance":     "0.8850",
      "authority":     "0.9800",
      "recency":       "0.9990",
      "topic":         "Science",
      "article_count": 108,
      "sources":       ["BBC World", "NASA Breaking", "Reuters"],
      "passed_gate":   true,
      "generated_at":  "2026-04-13T14:30:22+00:00"
    }
  ]
}
```

Only items with `passed_gate: true` are returned by the API Lambda.
The hook sorts by `score` descending. `DigestPage` filters by topic client-side.
