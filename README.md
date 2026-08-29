# Taashira · تأشيرة

**An agent that runs a student-visa campaign for applicants whose own identity documents
expire inside the plan.**

Built for the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/)
— Taskmaster track.

Live: https://taashira-api-871622321683.us-central1.run.app

---

## The problem

A visa application is usually modelled as a checklist. For most applicants that is close
enough. For an applicant holding a **travel document rather than a passport**, it is wrong
in a way that costs an academic year.

A Lebanese travel document for Palestinian refugees is valid for **five years with an UNRWA
vitality card, and one or three years without one**. A visa is never issued beyond the
validity of the document it is placed in. So a two-year masters programme can outlast the
document it depends on — and the renewal is not a prerequisite sitting outside the plan,
it is a **node inside the dependency graph**, with inputs of its own.

Those inputs have their own rules. The renewal needs an Individual Civil Extract **issued
within the last three years**, so an extract that was fine last year can go stale
mid-campaign and block the renewal that the visa depends on.

That is three levels of cascade before anyone has filled in a form. And the forms
themselves assume facts the applicant does not have: nationality fields, and the
214(b) presumption of immigrant intent rebutted by "ties to your home country", for
someone with no home state.

**This is not a checklist. It is a scheduling problem with temporal constraints.**

## What Taashira does

It models a campaign as a **dependency graph of documents with validity windows, scheduled
backwards from an immovable date** — the semester start. Then it runs in the background,
re-evaluates every day, and repairs the plan when a constraint breaks.

Given a stateless applicant with a one-year travel document and a two-year programme, it:

1. detects that the travel document cannot cover the programme, and **splices a renewal
   into the graph**;
2. detects that the renewal's own civil extract will be stale by the time it is used, and
   **splices a re-issue below that**;
3. reschedules everything downstream and reports that the January intake is
   **24 days infeasible**, naming the node responsible rather than saying "not enough time";
4. has an adversarial consular agent argue for refusal, citing only rules that exist in the
   loaded requirement pack.

Given the *same pack* and an applicant with an ordinary ten-year passport, it produces nine
nodes and no remediation at all. The cascade is a function of the applicant's documents,
not a hardcoded storyline.

## Architecture

```mermaid
flowchart LR
  SCH[Cloud Scheduler<br/>daily heartbeat] -->|publish| PS[(Pub/Sub<br/>campaign-tick)]
  PS -->|push + OIDC| W[Cloud Run: worker<br/>ADK agents]
  PS -.->|5 failed attempts| DLQ[(campaign-dead<br/>dead letter)]
  W --> VX[Vertex AI<br/>gemini-3.5-flash]
  W --> FS[(Firestore<br/>campaigns · versions<br/>events · actions)]
  API[Cloud Run: api<br/>FastAPI + SSE] --> FS
  BROWSER[Operator UI] -->|SSE| API
  PACKS[/requirement packs<br/>versioned YAML/] --> W
  PACKS --> API
```

### Two services, split by capability

| Service | Identity | Roles | Can call a model? |
|---|---|---|---|
| `taashira-api` | `taashira-api@` | `datastore.user`, `pubsub.publisher` | **No.** No `aiplatform.user` binding exists. |
| `taashira-worker` | `taashira-worker@` | + `pubsub.subscriber`, `aiplatform.user` | Yes — the only identity that can. |

The public surface physically cannot reach Vertex AI. That is enforced by IAM, not by
convention, so compromising the browser-facing service cannot spend on inference.

### The split that matters most

**The model never does arithmetic.** Constraint evaluation, backward scheduling, critical
path and feasibility are deterministic Python with unit tests. The model extracts facts from
documents and argues about evidence — jobs where judgement is the point. Dates are jobs where
being plausibly wrong is catastrophic.

### Agent topology — 7 LLM agents + 1 deterministic planner tool

```
CampaignOrchestrator            LlmAgent (root)
├── IntakePipeline              SequentialAgent
│   ├── DocumentExtractor       LlmAgent · multimodal · output_schema=ExtractedDocument
│   └── DossierReconciler       LlmAgent · output_schema=ApplicantDelta
├── RequirementFitter           LlmAgent · output_schema=CampaignSpec
├── plan_campaign               FunctionTool → deterministic planner   ← no LLM
├── ReviewLoop                  LoopAgent(max_iterations=3)
│   ├── ConsularCritic          LlmAgent · output_schema=RefusalFindings
│   └── DossierRepairer         LlmAgent · tools=[exit_loop]
└── ActionExecutor              LlmAgent · tools=[write_calendar, render_pack, draft_request]
```

### Failure tolerance

- **Hallucination is filtered, not trusted.** Every critic finding must cite an `authority`
  string that exists in the loaded pack, verbatim. Findings that cite anything else are
  discarded and counted — `GroundedFindings.grounding_rate` is a measured property, not a
  claim. Live runs against `gemini-3.5-flash` currently ground at 100%.
- **Loops are bounded.** `LoopAgent(max_iterations=3)`; `exit_loop` sets
  `tool_context.actions.escalate`.
- **Every agent has an `output_schema`.** Unparseable output is a visible failure, not a
  silently-accepted string.
- **Unknown is not pass.** Constraint evaluation is tri-state. A document with no recorded
  expiry routes its node to `needs_human_review` rather than quietly succeeding — the exact
  failure that loses a visa.
- **Redelivery cannot double-act.** Events and actions are keyed on
  `(campaign_id, version, kind, detail)` and written with Firestore `create`, so at-least-once
  delivery is deduplicated atomically.
- **Poison messages dead-letter** after 5 attempts instead of retrying forever.

## Requirement packs are data, not code

A corridor is one `(document held → destination + visa type)` route, and each one is a
versioned YAML file in [`packs/`](packs/). Adding a corridor is authoring a file.

Each requirement carries lead times, dependencies, temporal constraints, and an `authority`
citation. Referential integrity is enforced at parse time.

```yaml
- id: visa_interview
  authority: "US Dept of State: visa validity may not exceed the validity of the travel document"
  constraints:
    - kind: covers
      document: travel_document
      period: program
      remediation: renew_travel_document   # ← this one field is the cascade
```

Five constraint kinds: `valid_at`, `covers`, `max_age_at_use`, `min_seasoning`,
`not_before` / `not_after`.

**Lead times are estimates and the packs say so.** Fee amounts and validity rules are cited;
day counts are planning heuristics used to compute risk.

## Spin up from scratch

Prerequisites: Python 3.12+, the `gcloud` CLI, and a Google Cloud project with billing.

```bash
git clone <this repo> && cd Taashira-AI
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,agents]"

# Everything below runs with no cloud account at all:
.venv/bin/python -m pytest -q                      # 28 tests
TAASHIRA_USE_FIRESTORE=0 .venv/bin/uvicorn taashira.main:app --reload
# open http://localhost:8000
```

To deploy:

```bash
./scripts/setup-gcp.sh   <PROJECT_ID>   # APIs, Firestore, Pub/Sub topics, service accounts
./scripts/deploy.sh      <PROJECT_ID>   # build and deploy the API
./scripts/setup-async.sh <PROJECT_ID>   # Scheduler → Pub/Sub → worker push
```

See [`docs/deployment.md`](docs/deployment.md) for the live configuration and for three
Cloud Run gotchas that cost us time.

## Verifying it works

```bash
.venv/bin/python -m pytest -q
```

The planner tests are the real safety net. They assert the cascade fires at two levels, that
the control applicant produces none from the same pack, that an unknown expiry routes to human
review rather than passing, and that renewing the document heals the plan and removes the
remediation nodes.

End to end against the deployment:

```bash
gcloud scheduler jobs run taashira-daily-tick --location us-central1 --project <PROJECT_ID>
gcloud logging read 'resource.labels.service_name="taashira-worker"' --limit 20
```

## What is real and what is synthetic

Stated plainly, because overstating what runs is a scoring failure:

- **Real:** the planner, the cascade, the constraint engine, the Cloud Run services, the
  Firestore state and version history, the Pub/Sub push loop, the Cloud Scheduler heartbeat,
  and the adversarial critic — which runs against `gemini-3.5-flash` on Vertex AI and whose
  findings quoted above are its actual output.
- **Synthetic:** the applicant. Every document in [`taashira/fixtures.py`](taashira/fixtures.py)
  is fabricated. No real identity document, number, or personal record appears anywhere in
  this repository.
- **Never touched:** government and embassy portals. Taashira does not book appointments, does
  not submit applications, and does not automate any consular system. It assembles, schedules,
  argues, and warns. Every submission is made by a human.

## Stack

| Requirement | Used |
|---|---|
| Gemini 3.5 or newer | `gemini-3.5-flash` on Vertex AI (`global` endpoint) |
| Google agent framework | Google ADK 2.8 — `LlmAgent`, `SequentialAgent`, `LoopAgent`, `FunctionTool` |
| Google Cloud services | Cloud Run, Firestore, Pub/Sub, Cloud Scheduler, Cloud Build, Artifact Registry |

Python 3.12, Pydantic v2, FastAPI.

## Origin

The builder holds a travel document for Palestinian refugees issued by Lebanon. He obtained a
J-1 with the US Department of State sponsoring him, and it was smooth — an institution absorbed
the friction on his behalf. The masters application has nobody behind it, and the travel
document expires before the degree would end.

The friction here is **structural, not biographical**: it belongs to every refugee travel
document, every short-validity passport, and every applicant whose form has no correct answer
in the nationality field.
