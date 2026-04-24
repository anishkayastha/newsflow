# ─────────────────────────────────────────────────────────────────────────────
# NewsFlow — project Makefile
# Run `make help` to see all available commands.
#
# SETUP: copy config.mk.example to config.mk and fill in your values, then:
#   source config.mk   (or set the variables in your shell)
#
# All AWS commands assume `aws configure` has been run with valid credentials.
# ─────────────────────────────────────────────────────────────────────────────

# ── Load local config if it exists ───────────────────────────────────────────
-include config.mk

# ── Required variables (set in config.mk or shell env) ───────────────────────
AWS_ACCOUNT_ID   ?= YOUR_ACCOUNT_ID
AWS_REGION       ?= ap-southeast-1
MODEL_BUCKET     ?= newsflow-models-$(AWS_ACCOUNT_ID)
PIPELINE_BUCKET  ?= newsflow-pipeline-$(AWS_ACCOUNT_ID)
FRONTEND_BUCKET  ?= newsflow-frontend-$(AWS_ACCOUNT_ID)
CLOUDFRONT_ID    ?= YOUR_CLOUDFRONT_DISTRIBUTION_ID
ECR_REPO         ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/newsflow-consumer

# Lambda function names (must match what you created in the console)
FN_SCRAPER  ?= newsflow-scraper
FN_CONSUMER ?= newsflow-consumer
FN_API      ?= newsflow-api

.PHONY: help setup download-models \
        package-scraper package-api build-consumer \
        upload-models push-consumer \
        deploy-scraper deploy-api deploy-consumer deploy-backend \
        build-frontend deploy-frontend \
        deploy-all logs-scraper logs-consumer logs-api \
        test-scraper check-pipeline fresh-run clean

# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  NewsFlow — available make targets"
	@echo "  ─────────────────────────────────────────────────────────"
	@echo "  SETUP"
	@echo "    setup             Install all local dependencies"
	@echo "    download-models   Download SBERT + DistilBART and package for S3"
	@echo ""
	@echo "  BACKEND — build"
	@echo "    package-scraper   Zip scraper Lambda (backend/scraper/scraper.zip)"
	@echo "    package-api       Zip API Lambda     (backend/api/api.zip)"
	@echo "    build-consumer    Build consumer Docker image"
	@echo ""
	@echo "  BACKEND — deploy"
	@echo "    upload-models     Upload model tarballs to S3"
	@echo "    push-consumer     Tag + push consumer image to ECR"
	@echo "    deploy-scraper    Deploy scraper zip to Lambda"
	@echo "    deploy-api        Deploy api zip to Lambda"
	@echo "    deploy-consumer   Update consumer Lambda to latest ECR image"
	@echo "    deploy-backend    Full backend build + deploy (all three Lambdas)"
	@echo ""
	@echo "  FRONTEND"
	@echo "    build-frontend    npm run build inside frontend/"
	@echo "    deploy-frontend   Build + sync to S3 + invalidate CloudFront"
	@echo ""
	@echo "  ALL"
	@echo "    deploy-all        deploy-backend + deploy-frontend"
	@echo ""
	@echo "  DEBUG"
	@echo "    test-scraper      Invoke scraper async + tail logs (Ctrl+C to stop)"
	@echo "    check-pipeline    List latest articles files in S3 pipeline bucket"
	@echo "    fresh-run         Trigger scraper + watch consumer process articles"
	@echo "    logs-scraper      Tail scraper CloudWatch logs"
	@echo "    logs-consumer     Tail consumer CloudWatch logs"
	@echo "    logs-api          Tail api CloudWatch logs"
	@echo "    clean             Remove all build artifacts"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────

setup:
	@echo "→ Installing frontend dependencies..."
	cd frontend && npm install
	@echo "→ Installing backend script dependencies..."
	pip install sentence-transformers transformers torch --quiet
	@echo "✓ Setup complete. Next: make download-models"

download-models:
	@echo "→ Downloading SBERT + DistilBART (~700 MB, takes 5–15 min)..."
	python backend/scripts/download_and_package_models.py
	@echo "✓ Models packaged. Next: make upload-models"

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND — build
# ─────────────────────────────────────────────────────────────────────────────

package-api:
	@echo "→ Packaging API Lambda (linux/amd64)..."
	rm -rf backend/api/package backend/api/api.zip
	docker run --platform linux/amd64 --rm \
	  --entrypoint bash \
	  -v $(PWD)/backend/api:/var/task \
	  public.ecr.aws/lambda/python:3.12 \
	  -c "pip install -r /var/task/requirements.txt -t /var/task/package/ --quiet"
	cp backend/api/handler.py backend/api/package/
	cd backend/api/package && zip -r ../api.zip . -q
	rm -rf backend/api/package
	@echo "✓ backend/api/api.zip ready"

package-scraper:
	@echo "→ Packaging scraper Lambda (linux/amd64)..."
	rm -rf backend/scraper/package backend/scraper/scraper.zip
	docker run --platform linux/amd64 --rm \
	  --entrypoint bash \
	  -v $(PWD)/backend/scraper:/var/task \
	  public.ecr.aws/lambda/python:3.12 \
	  -c "pip install -r /var/task/requirements.txt -t /var/task/package/ --quiet"
	cp backend/scraper/handler.py backend/scraper/package/
	cd backend/scraper/package && zip -r ../scraper.zip . -q
	rm -rf backend/scraper/package
	@echo "✓ backend/scraper/scraper.zip ready"

build-consumer:
	@echo "→ Building consumer Docker image..."
	docker buildx build \
	  --platform linux/amd64 \
	  --provenance=false \
	  --output type=docker \
	  -t newsflow-consumer:latest \
	  backend/consumer/
	@echo "✓ Image built: newsflow-consumer:latest"

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND — deploy
# ─────────────────────────────────────────────────────────────────────────────

upload-models:
	@echo "→ Uploading models to s3://$(MODEL_BUCKET)/models/ ..."
	aws s3 cp backend/models/sbert.tar.gz      s3://$(MODEL_BUCKET)/models/sbert.tar.gz      --region $(AWS_REGION)
	aws s3 cp backend/models/distilbart.tar.gz s3://$(MODEL_BUCKET)/models/distilbart.tar.gz --region $(AWS_REGION)
	@echo "✓ Models uploaded"

push-consumer:
	@echo "→ Authenticating Docker to ECR..."
	aws ecr get-login-password --region $(AWS_REGION) \
	  | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	@echo "→ Tagging and pushing image..."
	docker tag newsflow-consumer:latest $(ECR_REPO):latest
	docker push $(ECR_REPO):latest
	@echo "✓ Image pushed to ECR"

deploy-scraper: package-scraper
	@echo "→ Deploying scraper Lambda..."
	aws lambda update-function-code \
	  --function-name $(FN_SCRAPER) \
	  --zip-file fileb://backend/scraper/scraper.zip \
	  --region $(AWS_REGION) \
	  --query 'LastModified' --output text
	@echo "✓ $(FN_SCRAPER) updated"

deploy-api: package-api
	@echo "→ Deploying API Lambda..."
	aws lambda update-function-code \
	  --function-name $(FN_API) \
	  --zip-file fileb://backend/api/api.zip \
	  --region $(AWS_REGION) \
	  --query 'LastModified' --output text
	@echo "✓ $(FN_API) updated"

deploy-consumer: build-consumer push-consumer
	@echo "→ Updating consumer Lambda to latest image..."
	aws lambda update-function-code \
	  --function-name $(FN_CONSUMER) \
	  --image-uri $(ECR_REPO):latest \
	  --region $(AWS_REGION) \
	  --query 'LastModified' --output text
	@echo "✓ $(FN_CONSUMER) updated"

deploy-backend: deploy-scraper deploy-api deploy-consumer
	@echo "✓ All backend Lambdas deployed"

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND
# ─────────────────────────────────────────────────────────────────────────────

build-frontend:
	@echo "→ Building React app..."
	cd frontend && npm run build
	@echo "✓ Build complete → frontend/dist/"

deploy-frontend: build-frontend
	@echo "→ Uploading assets (immutable cache)..."
	aws s3 sync frontend/dist/ s3://$(FRONTEND_BUCKET)/ \
	  --delete \
	  --region $(AWS_REGION) \
	  --cache-control "public, max-age=31536000, immutable" \
	  --exclude "index.html" \
	  --quiet
	@echo "→ Uploading index.html (no-cache)..."
	aws s3 cp frontend/dist/index.html s3://$(FRONTEND_BUCKET)/index.html \
	  --region $(AWS_REGION) \
	  --cache-control "no-cache, no-store, must-revalidate"
	@echo "→ Invalidating CloudFront..."
	aws cloudfront create-invalidation \
	  --distribution-id $(CLOUDFRONT_ID) \
	  --paths "/*" \
	  --query 'Invalidation.Id' --output text
	@echo "✓ Frontend deployed"

# ─────────────────────────────────────────────────────────────────────────────
# ALL
# ─────────────────────────────────────────────────────────────────────────────

deploy-all: deploy-backend deploy-frontend
	@echo ""
	@echo "✓ Full deployment complete"

# ─────────────────────────────────────────────────────────────────────────────
# DEBUG
# ─────────────────────────────────────────────────────────────────────────────

test-scraper:
	@echo "→ Invoking $(FN_SCRAPER) asynchronously..."
	aws lambda invoke \
	  --function-name $(FN_SCRAPER) \
	  --region $(AWS_REGION) \
	  --invocation-type Event \
	  --payload '{}' \
	  --cli-binary-format raw-in-base64-out \
	  /tmp/scraper-response.json
	@echo "✓ Scraper triggered — tailing logs (Ctrl+C to stop)..."
	aws logs tail /aws/lambda/$(FN_SCRAPER) \
	  --follow \
	  --region $(AWS_REGION)

check-pipeline:
	@echo "→ Latest articles files in s3://$(PIPELINE_BUCKET)/pipeline/"
	aws s3 ls s3://$(PIPELINE_BUCKET)/pipeline/ \
	  --region $(AWS_REGION) \
	  | sort | tail -5

fresh-run:
	@echo "→ Triggering scraper — articles will be written to S3..."
	aws lambda invoke \
	  --function-name $(FN_SCRAPER) \
	  --region $(AWS_REGION) \
	  --invocation-type Event \
	  --payload '{}' \
	  --cli-binary-format raw-in-base64-out \
	  /tmp/scraper-response.json
	@echo "✓ Scraper triggered. Consumer fires automatically when S3 file is written."
	@echo "  Run 'make logs-consumer' to watch the pipeline run."

logs-scraper:
	aws logs tail /aws/lambda/$(FN_SCRAPER) --follow --region $(AWS_REGION)

logs-consumer:
	aws logs tail /aws/lambda/$(FN_CONSUMER) --follow --region $(AWS_REGION)

logs-api:
	aws logs tail /aws/lambda/$(FN_API) --follow --region $(AWS_REGION)

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN
# ─────────────────────────────────────────────────────────────────────────────

clean:
	rm -rf backend/scraper/package backend/scraper/scraper.zip
	rm -rf backend/api/package backend/api/api.zip
	rm -rf frontend/dist
	@echo "✓ Build artifacts removed"