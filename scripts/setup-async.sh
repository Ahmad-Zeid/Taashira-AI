#!/usr/bin/env bash
#
# Wire the background loop: Cloud Scheduler -> Pub/Sub -> the worker's push endpoint.
# This is what makes the system run with no human present.
#
#   ./scripts/setup-async.sh [PROJECT_ID] [REGION]

set -euo pipefail

PROJECT="${1:-taashira-506919}"
REGION="${2:-us-central1}"
NUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
INVOKER="taashira-pubsub@${PROJECT}.iam.gserviceaccount.com"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()  { printf '    \033[32m✓\033[0m %s\n' "$*"; }

WORKER_URL=$(gcloud run services describe taashira-worker \
  --project "$PROJECT" --region "$REGION" --format='value(status.url)')
ok "worker at $WORKER_URL"

say "Push identity"
gcloud iam service-accounts create taashira-pubsub \
  --display-name="Pub/Sub push identity for the Taashira worker" \
  --project "$PROJECT" >/dev/null 2>&1 || ok "already exists"

# It may invoke the worker and nothing else.
gcloud run services add-iam-policy-binding taashira-worker \
  --project "$PROJECT" --region "$REGION" \
  --member="serviceAccount:${INVOKER}" --role=roles/run.invoker >/dev/null
ok "granted run.invoker on taashira-worker only"

# Pub/Sub's own service agent must be able to mint tokens as that identity.
gcloud iam service-accounts add-iam-policy-binding "$INVOKER" \
  --project "$PROJECT" \
  --member="serviceAccount:service-${NUM}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role=roles/iam.serviceAccountTokenCreator >/dev/null
ok "pubsub service agent may impersonate it"

say "Push subscription (with dead-letter)"
gcloud pubsub subscriptions delete campaign-tick-push --project "$PROJECT" --quiet >/dev/null 2>&1 || true
gcloud pubsub subscriptions create campaign-tick-push \
  --project "$PROJECT" \
  --topic=campaign-tick \
  --push-endpoint="${WORKER_URL}/pubsub/tick" \
  --push-auth-service-account="$INVOKER" \
  --ack-deadline=300 \
  --dead-letter-topic=campaign-dead \
  --max-delivery-attempts=5 >/dev/null
ok "campaign-tick -> ${WORKER_URL}/pubsub/tick, 5 attempts then dead-letter"

# The dead-letter mechanism needs Pub/Sub to be able to publish to the DLQ and ack the
# original; without these two bindings a poison message retries forever.
PUBSUB_AGENT="serviceAccount:service-${NUM}@gcp-sa-pubsub.iam.gserviceaccount.com"
gcloud pubsub topics add-iam-policy-binding campaign-dead \
  --project "$PROJECT" --member="$PUBSUB_AGENT" --role=roles/pubsub.publisher >/dev/null
gcloud pubsub subscriptions add-iam-policy-binding campaign-tick-push \
  --project "$PROJECT" --member="$PUBSUB_AGENT" --role=roles/pubsub.subscriber >/dev/null
ok "dead-letter bindings in place"

say "Daily heartbeat"
gcloud scheduler jobs delete taashira-daily-tick --project "$PROJECT" --location "$REGION" --quiet >/dev/null 2>&1 || true
gcloud scheduler jobs create pubsub taashira-daily-tick \
  --project "$PROJECT" --location "$REGION" \
  --schedule="0 7 * * *" --time-zone="Asia/Beirut" \
  --topic=campaign-tick \
  --message-body='{"source":"scheduler"}' \
  --description="Re-evaluate every active visa campaign against today's date" >/dev/null
ok "taashira-daily-tick: 07:00 Asia/Beirut, every day"

say "Done"
echo "    Force a run now:  gcloud scheduler jobs run taashira-daily-tick --location $REGION --project $PROJECT"
