#!/usr/bin/env bash
#
# Deploy the Taashira API to Cloud Run.
#   ./scripts/deploy.sh [PROJECT_ID] [REGION]
#
# Runs as the taashira-api service account, which deliberately has no Vertex AI
# access: this service serves the browser and runs the deterministic planner, and
# nothing it can reach costs money per token.

set -euo pipefail

PROJECT="${1:-taashira-506919}"
REGION="${2:-us-central1}"

gcloud run deploy taashira-api \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --service-account "taashira-api@${PROJECT}.iam.gserviceaccount.com" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},TAASHIRA_USE_FIRESTORE=0" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --quiet

URL=$(gcloud run services describe taashira-api \
        --project "$PROJECT" --region "$REGION" --format='value(status.url)')

echo
echo "Service URL: $URL"
curl -s "$URL/" | python3 -m json.tool
