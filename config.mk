# config.mk — copy this file to config.mk and fill in your values.
# config.mk is in .gitignore — never commit it.
#
# Usage: this file is auto-loaded by the Makefile via `-include config.mk`
# You do NOT need to source it manually.

export AWS_ACCOUNT_ID   = 181053172023
export AWS_REGION       = ap-southeast-1

# S3 buckets (created in AWS Console step 1 and frontend setup)
export MODEL_BUCKET     = newsflow-models-181053172023
export FRONTEND_BUCKET  = newsflow-frontend-181053172023

# CloudFront distribution ID (Console → CloudFront → your distribution)
export CLOUDFRONT_ID    = E6QGYDO6LSM6

# ECR image URI (auto-derived from account + region — usually no change needed)
export ECR_REPO         = 181053172023.dkr.ecr.ap-southeast-1.amazonaws.com/newsflow-consumer

# Lambda function names (must match what you named them in the Console)
export FN_SCRAPER       = newsflow-scraper
export FN_CONSUMER      = newsflow-consumer
export FN_API           = newsflow-api
