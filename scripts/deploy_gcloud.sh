#!/bin/sh
# Deploy API to Cloud Run (Artifact Registry). Needs: gcloud auth login.
# Usage: PROJECT=myproj REGION=europe-west1 ./scripts/deploy_gcloud.sh
set -e
PROJECT="${PROJECT:?set PROJECT}"; REGION="${REGION:-europe-west1}"
IMG="$REGION-docker.pkg.dev/$PROJECT/ib-resources/ib-resources:latest"
gcloud builds submit --tag "$IMG" --project "$PROJECT"
gcloud run deploy ib-resources --image "$IMG" --region "$REGION" \
  --project "$PROJECT" --allow-unauthenticated --port 8471 \
  --memory 512Mi --cpu 1 --max-instances 2
