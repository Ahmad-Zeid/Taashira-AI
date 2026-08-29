# All Things Agentic Hackathon — Full Reference

Compiled 2026-08-27 from the Devpost overview, Official Rules (raw HTML), Resources, FAQs, Updates,
and the discussion forum. **Where pages disagree, the Official Rules are binding.**

Published dossier: https://claude.ai/code/artifact/f35339aa-11c8-4706-a697-6bf4a51645a0

---

## Identity

- **Host:** Google. **Administrator:** Devpost. **Themes:** Enterprise, Machine Learning/AI, Productivity.
- **Site:** https://allthingsagentichackathon.devpost.com/
- **Registered participants:** 10,368 (as of Aug 27).
- **Prize pool:** $180,000 across 16 prizes.
- **Tagline:** "Ready, Set, Agent! Build next-generation agents that run in the background, handle the
  heavy lifting of massive datasets, and automate complex workflows asynchronously."
- **Framing (verbatim):** "Most AI today waits for you to ask. The next generation doesn't."

## What to build (Rules §6, verbatim)

> "Build and deploy a next-generation, autonomous AI Agent leveraging Gemini 3.5 that operates beyond
> standard chat loops. The system can run asynchronously in the background, handle the heavy lifting of
> complex workflows, or dynamically manipulate data pipelines and representations."

Mandatory for all categories:
1. Gemini 3.5 or newer via Gemini API or Vertex AI
2. AND ≥1 Google Agent Framework: Google ADK, GenAI SDK, Antigravity SDK, or Genkit
3. AND ≥1 Google Cloud infrastructure service (Cloud Run, Cloud SQL, Firestore, GKE, Pub/Sub)

**Deployment note (verbatim):** "Your app does not need to be publicly accessible or live at the exact
moment of submission or judging (so you don't rack up unnecessary costs). You just need to provide clear
proof that it was built and deployed on Google Cloud."

---

## The three tracks

### Taskmaster
> "Build a complete workflow, not just a chatbot. Don't just make an agent that writes text. Make one
> that takes action. Find a messy, multi-step chore in your job, classes, or personal life. Build an
> agent that handles the details, sends the right info to the right places, and proves it can do the
> heavy lifting for you."

**In-depth (Resources):** "An event-driven workflow with autonomous routing. Your system acts like a
smart coordinator — watching for a change, figuring out what needs to happen next, and interacting with
different apps to get the job done, from start to finish, without you guiding each step."

**Google's examples:** an "Automated Product Manager" that reads meeting transcripts, extracts action
items, creates Jira tasks and posts a Slack summary. A "Freelance Pipeline" agent that watches an inbox
for inquiries, checks the calendar, drafts a proposal from past work, and saves it for review.

**Judged on:** "Does the agent successfully intercept and complete a multi-step background workflow
without human intervention? Did the team successfully utilize the 'Bring Your Own Friction' (BYOF)
mandate to solve a unique, personal problem?"

**Architecture sub-criterion ("The Continuous Action Engine"):** "Did you implement a clean, modularized,
ease of maintenance system? How does the system handle state management? Are the tools properly isolated
and scoped for security?"

### Collaborative Partner
> "Build an agent that leads the way and takes notes. It should ask clarifying questions, guide the user
> step-by-step, and have a clear way to capture feedback, so it constantly adapts to the user's unique
> way of thinking."

**In-depth (Resources):** "Stateful, multi-turn dialogue with real-time context retrieval (RAG) and
persistent memory, so your agent adapts and personalizes based on past interactions instead of starting
over each time."

**Google's examples:** an expert guide through a dense legal document that quizzes you, learns which
concepts you struggle with, and adapts future explanations. A UI/UX helper for non-designers that turns
a vague idea into a wireframe and learns brand preferences from corrections.

**Judged on:** "Does the agent actively synthesize or mutate data, rather than just reading it? Did the
team ingest unusual, messy, or highly complex unstructured data streams?"

**Architecture sub-criterion ("The Evolving Knowledge Engine"):** "Intelligent schema design, efficient
vector embedding strategies. How efficiently does the system manage massive context windows?"

### Fortified Enterprise Fleet
> "Build a scalable network of institutional agents that hook into official enterprise infrastructure.
> Teams must demonstrate how agents are cataloged for cross-department use, how they safely maintain
> context across weeks of asynchronous operations, and how they interact with production data without
> violating enterprise compliance, data sovereignty, or security policies."

**In-depth (Resources):** "Corporate agent discovery, multi-agent orchestration at scale, long-term state
persistence, runtime observability, and security posture enforcement. Show how an organization can
discover your agents, audit their reasoning, trust their data handling, and scale them safely.
**Open to everyone — not just startups or enterprises.**"

**Recommended stack — Gemini Enterprise Agent Platform (GEAP)**, recommended not required, but the FAQ
says "they're what this track's judging is built around, and deploying on the Agent Platform earns bonus
points":
- **Agent Registry** — publishing, versioning, discovering enterprise-approved agents
- **Agent Runtime** — long-running, asynchronous background execution
- **Memory Bank** — persistent, secure cross-session context over extended timelines
- **Agent Identity** — zero-trust access control
- **Agent Gateway** — unified routing and policy enforcement
- **Model Armor** — inline guardrails against prompt injection, tool poisoning, PII leaks
- **Agent Observability** — OpenTelemetry-compliant audit logs and end-to-end reasoning-chain traces

**Google's example:** "An 'Enterprise Supply Chain Orchestrator' that a procurement manager finds in the
internal Agent Registry to run a multi-week vendor onboarding cycle — monitoring delivery webhooks,
remembering negotiation data via Memory Bank, securely querying private ERP inventory with Agent Identity,
coordinating with a logistics sub-agent through Agent Gateway, and screening all external email with
Model Armor."

**Judged on:** "Is the task complex enough to warrant a multi-agents system? Does the system intelligently
delegate tasks to specialized sub-agents? Did they build this for an 'Unlikely Hero' outside of standard
corporate roles?"

**Architecture sub-criterion ("The Multi-Agent Nexus"):** "Is there a clear, strictly enforced separation
of concerns between agents? Is the inter-agent routing logic failure-tolerant (e.g., how does the system
recover if a worker agent loops or returns a hallucination)?"

---

## Judging (Rules §8)

**Method:** "This process may utilize expert panels, peer review, **automated AI-driven analysis**, or any
combination thereof." Judges are not named — the site lists only "A qualified panel of Judges." Assume part
of the first pass may be machine-read; structure the written description accordingly.

**Stage One (pass/fail):** includes all submission requirements, reasonably addresses a Challenge,
reasonably applies the requirements.

**Stage Two:** 1–5 per criterion.
- **Innovation & Operational Utility — 40%.** "Does the system eliminate real-world friction? Is the
  'Twist' present? We are looking for high-value, autonomous execution over simple chat queries."
- **Architectural Discipline & Tech Stack — 30%.** "We are evaluating your engineering decisions, not just
  your ability to call an API. How well did your team decouple systems, manage state, and design robust,
  failure-tolerant agentic systems?"
- **Demo & Production Readiness — 30%.** "The clarity of the technical documentation and the undeniable
  proof of execution in the video pitch."
  - *Proof of Action:* "Does the video show an unedited, live execution of the agent performing its task
    (via terminal logs, database updates, or UI changes)?"
  - *Documentation:* "Does the public GitHub repository feature a clean architecture diagram and
    reproducible setup instructions? Is there visual proof of Google Cloud deployment in the video?"

**Stage Three (bonus, up to +1.0):** content write-up +0.2 · social post with #AllThingsAgenticHackathon
+0.2 · +0.2 per additional Google AI model (Gemma, Veo, Lyria) capped at 0.6.

**Final score: 1–6.** Highest scorer per category wins that track; highest across all categories wins Grand
Prize. **Ties broken criterion by criterion in listed order**, then judge vote.

---

## Prizes

| Prize | Cash | Winners | Extras | Eligibility |
|---|---|---|---|---|
| Grand Prize | $50,000 | 1 | $5,000 credits, coffee chat, social promo | Highest score overall |
| The Taskmaster | $20,000 | 1 | $2,000 credits, coffee, promo | That category |
| The Collaborative Partner | $20,000 | 1 | $2,000 credits, coffee, promo | That category |
| Fortified Enterprise Fleet | $20,000 | 1 | $2,000 credits, coffee, promo | That category |
| Startup Excellence | $20,000 | 1 | $5,000 credits, coffee, promo | Incorporated org + corporate email, opted in |
| Individual / Hobbyist | $10,000 | 2 | $1,000 credits each, coffee, promo | All individuals and teams |
| Best Architectural Design | $5,000 | 2 | $1,000 credits each | Top scorers on that criterion |
| Best Multimodal UX | $5,000 | 2 | $1,000 credits each | Top scorers on that criterion |
| Honorable Mentions | $2,000 | 5 | $500 credits each | Runners-up |

**Each Project is eligible for up to one (1) Prize.** Multiple submissions allowed but each must be
"unique and substantially different."

---

## Rules with teeth

- **Excluded residents:** Italy, Quebec, Crimea, Cuba, Iran, Syria, North Korea, Sudan, Belarus, Russia,
  and any country under U.S. sanctions. Google/Devpost employees and households ineligible.
- **New projects only.** Must be created during the Submission Period. Standard tools, frameworks,
  libraries, starter templates and AI coding assistants are explicitly allowed; anything else pre-existing
  must be disclosed.
- **No prior Google/Devpost financial or preferential support** for the project.
- **IP stays with the entrant.** Google gets a perpetual, irrevocable, worldwide, royalty-free,
  non-exclusive license for evaluation, promotion and advertising.
- **Open source permitted** if licenses are honored and the submission "enhances and builds upon the
  features and functionality included in the underlying open source product."
- **Post-deadline lock.** No edits to anything. Organizers warn that changing the repo, video or live site
  during judging "can put your prize eligibility at risk." Fork if you want to keep building.
- **Winner notification is a 2-day fuse.** No response within two days of the first attempt → disqualified,
  next-highest scorer promoted. Affidavit and tax forms due within 10 business days; payment within 60 days.
- **Governing law:** California. Disputes via JAMS binding arbitration in San Jose.

## Published contradictions

| Item | Rules page | Devpost tab |
|---|---|---|
| Submissions open | Aug 3, 9:00 AM PT | Aug 4, 7:45 AM PDT |
| Judging ends | Oct 1, 11:45 PM PT | Sep 24, 5:00 PM PDT |
| Credit form URL | `forms.gle/riGhgDSHkHeMx8Ca6` | Resources: `forms.gle/5PtXmw1dSbDnpYke9` |
| Model | "Gemini 3.5 or newer" | Overview "What to Build" says "Gemini 3.5 Flash" |

Assume the Rules. Credit form closed **Aug 28, 12:00 PM PT**; one request per entrant; reviewed within 72
*business* hours; FAQ warns that requests naming a non-existent track or with a too-short description are
auto-declined.

---

## Cost control (official guidance)

Gemini Flash first, Pro only for complex final reasoning · min instances = 0 so Cloud Run sleeps ·
small initial RAM/CPU with max-instance caps · serverless vector search, no always-on clusters ·
light storage footprint · billing budget alerts · protect public Cloud Run URLs with auth so stray
traffic can't drain credits · **record proof of the working deployment, then switch everything off.**

Credits do *not* cover: third-party Marketplace products billed through GCP (MongoDB Atlas, Datadog),
Cloud Domains registrations, some high-cost GPU/TPU reservations.

---

## Prior Google hackathon winners (pattern library)

| Event | Field | Grand prize | What it was |
|---|---|---|---|
| ADK Hackathon (2025) | 10,400 → 477 | **SalesShortcut** | Autonomous SDR: finds businesses with no web presence via Google Maps, researches them, writes a bespoke pitch, cold-calls with a synthetic voice, emails follow-ups. 34 agents (21 LLM, 7 sequential, 1 parallel, 2 custom, 1 loop) across 5 Cloud Run microservices over A2A. Became a company. |
| GKE Turns 10 (2025) | 4,773 → 133 | **Cart-to-Kitchen** | Solo. Two agents on GKE Autopilot extend an existing microservice app over gRPC; Gemini + Imagen recipes, fuzzy-matched cart additions. Headline: 30s → ~5s, 65% faster. Terraform + Skaffold. |
| Rapid Agent (2026) | 14,500 → 1,430 | **Unravel** | Built by a cancer geneticist. Five agents watch ClinVar/gnomAD/AlphaMissense for the moment a "variant of uncertain significance" turns clinically significant, then draft the clinician alert and family letter. |
| Gemini 3 (2026) | 35,616 registered | **Globot** | Multi-agent supply-chain crisis management: geopolitical signals, 2M-token compliance analysis, satellite imagery risk, financial impact of route changes, replanning around conflict zones. |

**Shared pattern:** a named professional's real job · output is an action with consequences, never a
summary · domain credibility the judges can smell · explicit agent count and topology · one hard measured
number · solo entries win regularly · education and shopping assistants are saturated and mostly land in
regional/honorable-mention slots.

**Estimated field here:** registration-to-submission runs 3–10% at comparable events → roughly 300–1,000
real submissions against 16 prizes.

---

## Link index

**Hackathon:** [Overview](https://allthingsagentichackathon.devpost.com/) ·
[Rules](https://allthingsagentichackathon.devpost.com/rules) ·
[Resources](https://allthingsagentichackathon.devpost.com/resources) ·
[FAQs](https://allthingsagentichackathon.devpost.com/details/faqs) ·
[Updates](https://allthingsagentichackathon.devpost.com/updates) ·
[Discussions](https://allthingsagentichackathon.devpost.com/forum_topics) ·
[Submission form](https://devpost.com/submit-to/30845-all-things-agentic-hackathon/manage/submissions)

**Build:** [ADK docs](https://google.github.io/adk-docs) · [adk-python](https://github.com/google/adk-python) ·
[Gemini API](https://ai.google.dev) · [AI Studio](https://aistudio.google.com) ·
[Antigravity SDK](https://antigravity.google/docs/sdk) · [Genkit](https://firebase.google.com/docs/genkit) ·
[Cloud Run](https://cloud.google.com/run) · [Firestore](https://cloud.google.com/firestore)

**GEAP:** [Overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/overview) ·
[Agent Runtime](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime) ·
[Memory Bank](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank)

**Workshops (recordings):**
[ADK orchestration patterns](https://cloudonair.withgoogle.com/events/architecting-multi-agent-teams-mastering-three-orchestration-patterns-adk-2) ·
[Long-running agents & idempotency](https://cloudonair.withgoogle.com/events/build-long-running-agent-persistent-workflows-google-adk) ·
[Self-evolving agents](https://cloudonair.withgoogle.com/events/build-self-evolving-agent-autonomous-self-improvement) ·
[Agent memory](https://cloudonair.withgoogle.com/events/architecting-agent-memory-session-state-vector-search-managed-cloud-memory)

**Private repo access:** `testing@devpost.com`, `cloudhackathons@google.com`
