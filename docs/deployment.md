# Deployment

Live as of 2026-08-28.

| | |
|---|---|
| **Project** | `taashira-506919` |
| **Region** | `us-central1` |
| **Service URL** | https://taashira-api-871622321683.us-central1.run.app |
| **Firestore** | `(default)`, native mode, `nam5` |
| **Pub/Sub** | `campaign-tick`, `campaign-events`, `campaign-dead` |
| **Model** | `gemini-3.5-flash` on Vertex AI, `global` endpoint |
| **Worker** | https://taashira-worker-zh7csmrgia-uc.a.run.app (private) |
| **Schedule** | `taashira-daily-tick` → `campaign-tick` → worker push endpoint |
| **Free trial** | $300, expires 2026-11-27 |

## Pass/fail gates — all three satisfied

| Gate | How | Evidence |
|---|---|---|
| Gemini 3.5 or newer | `gemini-3.5-flash` via Vertex AI | `generateContent` returns 200; `modelVersion: gemini-3.5-flash` |
| Google agent framework | Google ADK | wired in F4 |
| Google Cloud service | Cloud Run + Firestore + Pub/Sub | service live, database and topics created |

## Reproducing

```bash
./scripts/setup-gcp.sh <PROJECT_ID>   # once: APIs, Firestore, topics, service accounts
./scripts/deploy.sh <PROJECT_ID>      # build and deploy the API
```

## Identities

Two service accounts, split so that a compromise of the public surface cannot spend
on inference:

| Identity | Roles | Notes |
|---|---|---|
| `taashira-api` | `datastore.user`, `pubsub.publisher` | **No** `aiplatform.user`. Serves the browser; cannot call a model. |
| `taashira-worker` | `datastore.user`, `pubsub.{publisher,subscriber}`, `aiplatform.user` | The only identity permitted to reach Vertex AI. |

## Things that bit us, recorded so they do not bite again

- **`/healthz` is unreachable on Cloud Run.** Google's frontend intercepts that exact
  path and returns its own 404 before the request reaches the container. The route
  worked in local tests and 404'd in production. Health is served at `/` and
  `/api/health` instead.
- **Cloud Build needs IAM that a new project does not grant.** The default compute
  service account requires `storage.objectViewer`, `logging.logWriter` and
  `artifactregistry.writer`, or `gcloud run deploy --source` fails at "could not
  resolve source".
- **Heavy gRPC dependencies broke the image build.** `google-cloud-firestore` and
  `google-cloud-pubsub` in the API image caused the Docker build step to fail. The API
  does not need them — it runs the planner and serves JSON — so `requirements-api.txt`
  is kept deliberately minimal. The worker image will carry the cloud clients.

## The autonomous loop, verified in production

Cloud Scheduler fired unattended at `2026-08-29T01:35:00Z` and the chain ran with no
human involved:

```
{"as_of":"2026-08-27","campaigns":0,"event":"tick.start"}
{"campaign_id":"cmp_78435043a1cc","event":"campaign.seeded","feasible":false,"nodes":13}
{"as_of":"2026-08-27","campaigns":1,"event":"tick.start"}
{"campaign_id":"cmp_78435043a1cc","event":"plan.unchanged"}
{"campaigns":1,"changed":0,"event":"tick.done"}
```

Firestore afterwards: one campaign, version 1, 13 nodes, 10 events, and the cascade
persisted — `renew_travel_document` at depth 1, `reissue_civil_extract` at depth 2.

Note the second and third ticks: `plan.unchanged`, no events emitted. Silence on a
quiet day is the designed behaviour, and it is what makes an alert mean something.

The schedule is `*/5 * * * *` while filming. Set it back to daily (`0 7 * * *`,
`Asia/Beirut`) before submission.

## Cost posture

`--min-instances 0` so the service sleeps when idle, `--max-instances 3` to cap
runaway spend, 512Mi. The hackathon credit pool was exhausted before we requested it,
so this runs on the free trial: keep it asleep, and switch it off after the demo
footage is captured.
