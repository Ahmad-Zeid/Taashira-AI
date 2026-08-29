# Veeza AI — Competitive Research & the Student-Visa Differentiation

Compiled 2026-08-27. Veeza AI is the closest existing analogue to this project and the reference
point the idea was framed against.

---

## 1. What Veeza AI is

**One-liner (their YC listing):** "AI travel agent for people with weak passports, starting with visas."

| | |
|---|---|
| **Batch** | Y Combinator **Fall 2026** |
| **Founder** | Aly Moursy (solo — YC team size listed as 1) |
| **YC partner** | Grey Baker |
| **Base** | Cairo, Egypt |
| **Tags** | AIOps · Consumer · AI |
| **Site** | https://veeza.ai |
| **Funding** | Bootstrapped as of Aug 2026 ("that's going to change soon") |

**Founder background:** electrical & communications engineering at Carleton University (Canada);
first intern at **BitAccess (YC S14)**; three years at Bell Canada as PM / UX lead in their Graduate
Leadership Program; founded Seeqe (2014); co-founded **Dlvvr**, a same-day delivery Shopify app
bootstrapped to ~$50k revenue and one of Shopify's highest-rated delivery apps; then Head of Product
and AI at **Efreshli**, where he shipped an AI interior-design product.

**Timeline:** closed beta 19 Apr 2026 → public beta June 2026 → hard launch planned Sept 2026.

**Traction (self-reported, Aug 2026):** ~700 weekly support inquiries; ~20% from outside Egypt —
Ethiopia, Nigeria, Cameroon, Indonesia, India, Bangladesh, and Global South nationals living in the US.

---

## 2. What Veeza actually does — the pipeline

Their public flow is three steps ("Pick a destination, upload your passport, and answer a few
questions"), but the machinery underneath is a genuine multi-stage agent pipeline:

1. **Intake** — AI chat assistant collects trip details in natural language; user picks destination
   and dates.
2. **Document ingestion** — passport photo uploaded; details extracted automatically; **Arabic text
   translated to English**; data reformatted for the destination's specific application forms.
3. **Adversarial verification** — "an adversarial AI model runs a first pass, flagging missing items
   or potential errors" against that embassy's requirements. *This is the most interesting piece of
   their architecture: a second model whose job is to try to fail the application.*
4. **Human expert review** — "Every application is reviewed by a real person before it goes anywhere."
5. **Appointment hunting** — a persistent agent watches embassy systems around the clock; when a slot
   opens it books it and notifies the user.
6. **Notification** — real-time **WhatsApp** updates throughout.
7. **Output** — a complete, print-ready application package.
8. **Visa Vault** — extracted documents stored for reuse on future applications.

**Coverage:** ~20 countries, ~10 fully self-serve. Full service (form fill + appointment booking) for
Croatia, UK, US, Slovakia, Finland, Sweden, Estonia, Denmark, Malta, Greece, Norway. Paperwork-only for
France and Netherlands. Concierge for Cyprus, Canada, Thailand, Georgia, Japan, Armenia and others.

**Pricing:** fixed fee per completed application, EGP ~750 (paperwork-only) to EGP ~4,000 (complex
destinations). Group discounts up to 25% for 5+ travellers. A **B2B subscription tier for travel
agencies with SLAs** is in development.

**Guarantee:** explicitly "No honest service can promise approval." Refunds only if Veeza fails to
deliver its own service.

---

## 3. Their stated thesis (useful, quotable, and worth arguing with)

- On the problem: "a 50-year old humiliating process" — "weeks of document gathering, opaque checklists
  that change without notice, appointment slots that vanish before you can book them, and brokers who
  charge a premium."
- On market size: "People in the Global North rarely need tourist visas. Yet **70% of all global visas
  are tourist or short-stay visas.**"
- On why incumbents miss it: "General models built in the West won't solve Global South problems because
  they don't experience them."
- **On why humans stay in the loop** — the most important line for us: "Human orchestrators possess
  real-time domain strategy outside the AI's training data — such as sudden policy updates issued by
  embassies in the last 24 hours." He expects frontier models to hit near-perfect accuracy on standard
  workflows within 12–24 months, but keeps humans because the stakes are high.

---

## 4. How close can we get, and where we should diverge

**Directly reusable, no reason to differ:** document ingestion + extraction, the adversarial
verification pass, persistent background monitoring, per-user document vault, push notifications,
a "package ready to submit" as the artifact of value.

**Where the student pivot is a genuinely different product, not a reskin:**

| | Tourist visa (Veeza) | Student visa (us) |
|---|---|---|
| **Time horizon** | Days to weeks | **6–12 months**, spanning admissions cycle → funding proof → visa → intake date |
| **Dependency shape** | Mostly a checklist | A **cascading chain** where each artifact unlocks the next: offer → deposit → I-20/CAS/admission letter → SEVIS/IHS fee → appointment → interview → visa → intake |
| **Failure cost** | A cancelled trip | **A lost academic year**, plus a forfeited tuition deposit and possibly a withdrawn offer |
| **Data ingested** | Passport, bank statement, itinerary | Passport, transcripts, degree certificates, language test scores, financial sponsor letters, blocked-account confirmations, admission letters — often in a second language |
| **Per-country machinery** | One form + one appointment | Country-specific *sub-systems*: US I-20 + SEVIS I-901 ($350) + DS-160 + $185 fee; Germany's mandatory **APS** certificate (3–12 weeks, gates both the university application *and* the VFS appointment); plus CAS/IHS, blocked accounts, attestation letters — each with their own deadlines |
| **Deadlines** | Self-imposed | **Externally imposed and immovable** — semester start dates, uni-assist cutoffs, deposit deadlines |
| **Rejection mechanics** | Weak ties / intent | Same, *plus* documented traps: a lump-sum deposit days before applying without a provable source is a near-automatic refusal; SEVIS typos cause delays and refusals |

**The strategic read:** Veeza's product is a *transaction* — get one application out the door.
A student-visa agent is a **campaign** — hold a plan together across months, notice when one link in
the chain slips, and re-plan the rest around it. That is a different and harder machine, and it is
the exact machine this hackathon is asking for.

---

## 5. Why this maps unusually well onto the hackathon rubric

*(See `CLAUDE.md` §3–§4 for the rubric and the hidden mandates.)*

- The hackathon's headline ask is agents that **"run in the background… and automate complex workflows
  asynchronously."** A tourist visa barely justifies that. A student visa cannot be done any other way.
- **Fortified Enterprise Fleet's** recommended stack reads like a spec written for this problem:
  **Agent Runtime** ("long-running, asynchronous background execution") and **Memory Bank**
  ("persistent, secure cross-session context **over extended timelines**"). A months-long visa campaign
  is the natural use case.
- **"Bring Your Own Friction" (Taskmaster)** rewards solving *a unique, personal problem*. If the
  builder has personally been through a weak-passport student visa process, that is the mandate,
  satisfied honestly, with domain credibility judges can feel.
- **"Unlikely Hero" (Fleet)** rewards building for someone outside standard corporate roles. A 19-year-old
  in Cairo or Lagos assembling a German APS file is about as far from "procurement manager" as it gets.
- **Collaborative Partner** rewards ingesting "unusual, messy, or highly complex unstructured data
  streams" and *mutating* rather than reading data. Bank statements, foreign-language transcripts and
  embassy PDFs that change without notice qualify on every count.
- **Best Multimodal UX** ($5,000 × 2, an undefended lane — see `CLAUDE.md` §9): document photography,
  passport/transcript vision, and spoken interview preparation are inherently multimodal, and the same
  work doubles as bonus-point model integrations.
- Prior grand prizes all went to **a named professional's real job** where the output was **an action
  with consequences**. "Assembled and filed a student's complete visa package, and held the deadline
  chain together for four months" is that shape.

---

## 6. Risks to resolve before building

1. **Do not automate embassy or government portals.** Veeza does appointment-hunting as a business with
   humans and accountability behind it; a hackathon demo that scrapes or scripts a real consular booking
   system is a ToS and legal problem, and Google's judges are unlikely to reward it. We need a design
   that demonstrates real autonomous action **without** touching live government infrastructure. This is
   the single biggest architectural constraint and it should be settled first.
2. **Judges want "unedited live execution."** Whatever the agent does on camera must genuinely happen.
   Anything mocked or seeded must be labelled as such in the README and the video — the organizers call
   out overstating what runs as a scoring failure.
3. **Veeza keeps humans in the loop deliberately; the rubric rewards autonomy.** These pull in opposite
   directions. The resolution is to make the human checkpoint an *explicit, designed* control surface
   (approval gates, confidence thresholds, escalation) rather than a gap in the automation — and to say
   so, because "failure tolerance" and "how does the system recover" are literally in the architecture
   criterion.
4. **Sensitive personal data.** Passports, financial records and immigration status are PII of the most
   consequential kind. Handle it properly in the demo (synthetic documents), and make the handling
   visible — it maps straight onto Model Armor / Agent Identity and the "credential security" language
   in the 30% criterion.
5. **The education-assistant category is saturated** in prior Google hackathons and mostly wins regional
   and honorable-mention slots. The defence is that this is not an education product — it is an
   immigration-logistics product whose user happens to be a student.

## 7. Facts to verify before asserting them publicly

Verified above: F-1 mechanics (I-20 / SEVIS I-901 $350 / DS-160 / $185 / 2–3 months); Germany's APS
(mandatory for Indian applicants since 1 Nov 2022, issued by the Academic Evaluation Centre at the
German Embassy in New Delhi, 3–12 weeks, gates both application and VFS appointment; uni-assist winter
deadline 15 Jul); the lump-sum-deposit and SEVIS-typo refusal triggers; US wait-time pressure in
Lagos/Abuja and India with student prioritisation.

**Not yet verified — check before putting in the video or README:** UK CAS / IHS surcharge amounts and
the 28-day maintenance-funds rule; Canada's study permit, PAL/TAL and GIC requirements; Australia's
Genuine Student criterion; Germany's blocked-account amount; France's Études en France procedure.

---

## Sources

- [Veeza AI on Y Combinator](https://www.ycombinator.com/companies/veeza-ai)
- [veeza.ai](https://www.veeza.ai/en)
- [EnterpriseAM Egypt — founder profile, 10 Aug 2026](https://enterpriseam.com/egypt/2026/08/10/one-egyptian-founder-and-ai-enthusiast-is-out-to-fix-the-broken-visa-process-plaguing-residents-of-the-global-south/)
- [Aly Moursy on LinkedIn](https://eg.linkedin.com/in/alymoursy)
