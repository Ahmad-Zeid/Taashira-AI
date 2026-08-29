"""Reading identity documents.

The one place a model is allowed to look at a photograph of someone's papers. It reports
what it can read and, importantly, what it *could not* — an unreadable expiry date is a
different thing from an absent one, and only the first should stop a plan.

Raw bytes are passed inline to the model and never persisted. What survives is the
extracted dates and a redacted reference, which is all the planner needs.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from taashira.agents.run import Attachment, run_structured
from taashira.agents.schemas import ExtractedDocument
from taashira.config import Settings
from taashira.domain.documents import IdentityDocument, VerificationSource

#: Below this, the document is recorded but its node routes to human review rather than
#: being trusted to satisfy a constraint. Visa dates are not a place for a confident guess.
CONFIDENCE_FLOOR = 0.75

INSTRUCTION = """\
You read identity and supporting documents for a visa application. Report only what is
legible in the image.

Rules:

1. Dates must be returned as ISO `YYYY-MM-DD`. Many documents print DD/MM/YYYY or use a
   non-Gregorian calendar — convert carefully, and if you cannot determine the order with
   certainty, leave the field null and name it in `unreadable_fields`.
2. Never guess. A null with the field listed in `unreadable_fields` is a correct answer; a
   plausible invented date is the worst possible answer, because it will silently satisfy a
   constraint that should have failed.
3. `reference_redacted` takes the LAST FOUR characters of any document number and nothing
   else. Never return a full passport or document number.
4. `confidence` reflects how sure you are of the DATES specifically, since those decide
   whether the plan holds.
5. Distinguish a travel document from a passport. A refugee travel document, a laissez-passer
   or a certificate of identity is `travel_document`, not `passport`, even where the layout
   imitates one.
"""


def build_document_extractor(config: Settings) -> LlmAgent:
    return LlmAgent(
        name="DocumentExtractor",
        model=config.model,
        description="Reads dates and issuer from a photographed identity document.",
        instruction=INSTRUCTION,
        output_schema=ExtractedDocument,
        output_key="extracted_document",
    )


async def extract_document(
    data: bytes, mime_type: str, *, config: Settings, hint: str | None = None
) -> ExtractedDocument:
    prompt = "Read this document and report what is legible."
    if hint:
        prompt += f"\nThe applicant says this is: {hint}"
    return await run_structured(
        build_document_extractor(config),
        prompt,
        ExtractedDocument,
        config=config,
        attachments=[Attachment(data=data, mime_type=mime_type)],
    )


def to_identity_document(
    extracted: ExtractedDocument, *, source_asset_id: str | None = None
) -> IdentityDocument:
    """Convert an extraction into a dossier record.

    Always `EXTRACTED`, never confirmed. Promotion to `USER_CONFIRMED` is a human act.
    """
    return IdentityDocument(
        kind=extracted.kind,
        issuer=extracted.issuer,
        issued_on=extracted.issued_on,
        expires_on=extracted.expires_on,
        reference_redacted=extracted.reference_redacted,
        source_asset_id=source_asset_id,
        extraction_confidence=extracted.confidence,
        verified_by=VerificationSource.EXTRACTED,
        attributes={"unreadable": ",".join(extracted.unreadable_fields)}
        if extracted.unreadable_fields
        else {},
    )


def needs_review(extracted: ExtractedDocument) -> bool:
    """Whether a human must look before this document is trusted."""
    return bool(extracted.unreadable_fields) or extracted.confidence < CONFIDENCE_FLOOR
