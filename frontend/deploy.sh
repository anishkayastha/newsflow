#!/bin/bash
# deploy.sh — builds the React app and pushes it to S3.
# Run this from the newsflow-frontend/ directory.
# Usage: ./deploy.sh

set -e  # exit on any error

# ── Config — fill these in once ────────────────────────────────────────────
S3_BUCKET="newsflow-frontend-YOUR_ACCOUNT_ID"     # from AWS Console → S3
CLOUDFRONT_ID="EXXXXXXXXXXXXXXXXX"                 # from AWS Console → CloudFront → your distribution ID
AWS_REGION="ap-southeast-1"                        # must match your deployment region
# ───────────────────────────────────────────────────────────────────────────

echo "Building..."
npm run build

echo "Uploading to s3://$S3_BUCKET ..."
aws s3 sync dist/ s3://$S3_BUCKET \
  --delete \
  --region $AWS_REGION \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"

# index.html must NOT be cached — browsers need the latest version on every visit
aws s3 cp dist/index.html s3://$S3_BUCKET/index.html \
  --region $AWS_REGION \
  --cache-control "no-cache, no-store, must-revalidate"

echo "Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"

echo "Done. Your digest is live."
