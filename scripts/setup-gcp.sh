#!/usr/bin/env bash
#
# Provision the Google Cloud resources Taashira needs.
#
# PREREQUISITES (these need a human — they involve an account and a card):
#   1. A Google Cloud project exists.
#   2. Billing is linked to it.
#   3. gcloud is installed and authenticated:
#        brew install --cask google-cloud-sdk
#        gcloud auth login
#        gcloud auth application-default login
#
# Then:  ./scripts/setup-gcp.sh <PROJECT_ID> [REGION]
#
# Idempotent: every step tolerates already existing. Safe to re-run.

set -euo pipefail

PROJECT="${1:?usage: setup-gcp.sh <PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"

# Firestore names its multi-region for the US differently from Cloud Run regions.
FIRESTORE_LOCATION="nam5"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()  { printf '    \033[32m✓\033[0m %s\n' "$*"; }

say "Project $PROJECT (region $REGION)"
gcloud config set project "$PROJECT" >/dev/null
gcloud config set run/region "$REGION" >/dev/null

if ! gcloud beta billing projects describe "$PROJECT" --format='value(billingEnabled)' 2>/dev/null | grep -q True; then
  echo "    ERROR: billing is not enabled on $PROJECT."
  echo "    Vertex AI, Cloud Run and Pub/Sub all require an active billing account."
  exit 1
fi
ok "billing enabled"

say "Enabling APIs (slow the first time)"
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com
ok "APIs enabled"

say "Firestore (native mode)"
if gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  ok "database already exists"
else
  gcloud firestore databases create --location="$FIRESTORE_LOCATION" --type=firestore-native
  ok "database created in $FIRESTORE_LOCATION"
fi

say "Pub/Sub topics"
# campaign.tick     — the daily heartbeat that makes this a background agent
# campaign.events   — plan changes, at-risk nodes, required actions
# campaign.dead     — poison messages, so a bad event cannot wedge the worker
for topic in campaign-tick campaign-events campaign-dead; do
  if gcloud pubsub topics describe "$topic" >/dev/null 2>&1; then
    ok "topic $topic exists"
  else
    gcloud pubsub topics create "$topic" >/dev/null
    ok "topic $topic created"
  fi
done

say "Service accounts (least privilege, one per service)"
create_sa() {
  local name="$1" display="$2"
  if gcloud iam service-accounts describe "${name}@${PROJECT}.iam.gserviceaccount.com" >/dev/null 2>&1; then
    ok "$name exists"
  else
    gcloud iam service-accounts create "$name" --display-name="$display" >/dev/null
    ok "$name created"
  fi
}
create_sa taashira-api    "Taashira API (serves the browser; never calls a model)"
create_sa taashira-worker "Taashira worker (runs agents; never serves the browser)"

grant() {
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:$1@${PROJECT}.iam.gserviceaccount.com" \
    --role="$2" --condition=None >/dev/null
}

say "IAM bindings"
# The API reads and writes campaign state and publishes events. It has no model access:
# if it is ever compromised it cannot spend on inference.
grant taashira-api    roles/datastore.user
grant taashira-api    roles/pubsub.publisher
ok "api: datastore.user, pubsub.publisher"

# The worker is the only identity that may call Vertex AI.
grant taashira-worker roles/datastore.user
grant taashira-worker roles/pubsub.publisher
grant taashira-worker roles/pubsub.subscriber
grant taashira-worker roles/aiplatform.user
ok "worker: datastore.user, pubsub.{publisher,subscriber}, aiplatform.user"

say "Done"
cat <<SUMMARY
    project   $PROJECT
    region    $REGION
    firestore (default) in $FIRESTORE_LOCATION
    topics    campaign-tick, campaign-events, campaign-dead
    identities taashira-api, taashira-worker

    Next: deploy the api service, then capture the Cloud Run dashboard on video
    before anything is torn down. That proof cannot be recreated later.
SUMMARY
