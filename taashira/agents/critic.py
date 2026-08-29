"""The adversarial consular officer.

The point of the product in one agent: fail the application here, so it does not fail
at the embassy. It reads the assembled dossier and the planned campaign and argues for
refusal.

Its one hard constraint is that every finding must cite an `authority` string that
actually appears in the loaded requirement pack. Findings that cite anything else are
discarded before they reach a human. That is the difference between an adversarial
reviewer and a machine that invents immigration law.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from taashira.agents.schemas import GroundedFindings, RefusalFindings
from taashira.config import Settings
from taashira.domain.campaign import Campaign
from taashira.domain.documents import Applicant
from taashira.domain.requirements import RequirementPack

INSTRUCTION = """\
You are a consular officer reviewing a student visa application. Your job is to refuse it
if there is any defensible ground to do so. You are not the applicant's advocate.

You will be given:
  - the applicant's documents, with issue and expiry dates
  - the planned campaign, including any constraint violations already detected
  - the requirement pack, each requirement carrying an `authority` citation

Rules you must follow:

1. Every finding MUST cite, verbatim, one of the `authority` strings from the pack you
   were given. Do not paraphrase it. Do not invent a regulation, a form number, a fee,
   or a processing time. If you cannot ground an objection in one of those strings, do
   not raise it.
2. Do not repeat a constraint violation the planner has already found unless you can add
   something an officer would actually say about it.
3. Prefer evidentiary and credibility grounds, which the planner cannot compute: an
   applicant with no nationality cannot demonstrate "ties to a home country" in the
   ordinary way, and the officer will notice if the answer is simply left blank.
4. Be specific. "Insufficient funds" is useless. "Balance appeared 7 days before the
   interview with no explicable source" is a finding.

Return a verdict and your findings in the required schema. Two sentences of summary,
no more.
"""


def build_consular_critic(config: Settings) -> LlmAgent:
    return LlmAgent(
        name="ConsularCritic",
        model=config.model,
        description="Argues for refusal of a visa application, citing only the loaded pack.",
        instruction=INSTRUCTION,
        output_schema=RefusalFindings,
        output_key="refusal_findings",
    )


def ground_findings(raw: RefusalFindings, pack: RequirementPack) -> GroundedFindings:
    """Discard findings that cite an authority the pack does not contain.

    This runs on every critic response. It is deterministic, it is cheap, and it is the
    concrete answer to "how does the system recover if a worker agent returns a
    hallucination".
    """
    permitted = pack.authorities
    kept, dropped = [], []
    for finding in raw.findings:
        (kept if finding.authority in permitted else dropped).append(finding)

    return GroundedFindings(
        verdict=raw.verdict,
        findings=kept,
        summary=raw.summary,
        dropped=dropped,
    )


def build_review_prompt(applicant: Applicant, campaign: Campaign, pack: RequirementPack) -> str:
    """Everything the critic is allowed to reason from, and nothing else."""
    documents = "\n".join(
        f"  - {d.kind}: issued {d.issued_on or 'unknown'}, "
        f"expires {d.expires_on or 'unknown'}, issuer {d.issuer or 'unknown'}"
        for d in applicant.documents
    )
    violations = (
        "\n".join(f"  - [{v.severity}] {v.requirement_id}: {v.detail}" for v in campaign.violations)
        or "  (none detected by the planner)"
    )
    authorities = "\n".join(f"  - {a}" for a in sorted(pack.authorities))

    return f"""\
CORRIDOR: {pack.corridor}
APPLICANT STATUS: {applicant.nationality_status}, resident in {applicant.residence_country}
PROGRAMME: {campaign.program.start} to {campaign.program.end}
PLAN FEASIBLE: {campaign.feasible}
BINDING CONSTRAINT: {campaign.binding_constraint or "none"}

DOCUMENTS ON FILE:
{documents}

VIOLATIONS ALREADY DETECTED BY THE PLANNER:
{violations}

AUTHORITIES YOU MAY CITE (verbatim, exactly one per finding):
{authorities}
"""
