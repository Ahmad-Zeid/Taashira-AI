"""Identity documents and the applicant who holds them.

The deliberate choice here is that the applicant holds *documents*, not a passport.
A passport is one `DocumentKind` among several, and nothing in the model assumes the
applicant has one, or has a nationality at all. That assumption is what every visa
form makes and what the applicants this product exists for cannot satisfy.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from taashira.domain.temporal import Interval


class DocumentKind(StrEnum):
    # Identity and travel
    PASSPORT = "passport"
    TRAVEL_DOCUMENT = "travel_document"
    REFUGEE_ID = "refugee_id"
    UNRWA_REGISTRATION = "unrwa_registration"
    CIVIL_EXTRACT = "civil_extract"
    RESIDENCE_PERMIT = "residence_permit"
    # Academic
    ADMISSION_LETTER = "admission_letter"
    I20 = "i20"
    TRANSCRIPT = "transcript"
    DEGREE_CERTIFICATE = "degree_certificate"
    LANGUAGE_TEST = "language_test"
    APS_CERTIFICATE = "aps_certificate"
    # Financial
    FINANCIAL_STATEMENT = "financial_statement"
    SPONSOR_LETTER = "sponsor_letter"
    BLOCKED_ACCOUNT = "blocked_account"
    # Process artefacts
    SEVIS_RECEIPT = "sevis_receipt"
    VISA_APPLICATION_FORM = "visa_application_form"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"


class NationalityStatus(StrEnum):
    """How the applicant's status maps onto the nationality a form expects.

    `STATELESS` and `REFUGEE_TRAVEL_DOCUMENT` select different requirement branches
    than `NATIONAL` does — that branching is the point.
    """

    NATIONAL = "national"
    STATELESS = "stateless"
    REFUGEE_TRAVEL_DOCUMENT = "refugee_travel_document"
    CONTESTED = "contested"


class VerificationSource(StrEnum):
    EXTRACTED = "extracted"  # model read it off an uploaded image; treat as provisional
    USER_CONFIRMED = "user_confirmed"
    HUMAN_REVIEWED = "human_reviewed"


class IdentityDocument(BaseModel):
    """One document the applicant holds or must obtain.

    Raw scans are never stored on this record — only `source_asset_id`, a pointer.
    Document numbers are held redacted; nothing downstream needs the full value.
    """

    kind: DocumentKind
    issuer: str | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    reference_redacted: str | None = Field(
        default=None,
        description="Last few characters only, so the applicant can tell which document this is.",
    )
    source_asset_id: str | None = None
    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    verified_by: VerificationSource = VerificationSource.EXTRACTED
    attributes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _dates_ordered(self) -> IdentityDocument:
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError(
                f"{self.kind}: expiry {self.expires_on} precedes issue {self.issued_on}"
            )
        return self

    @property
    def validity(self) -> Interval | None:
        """The window this document is valid for, when both endpoints are known."""
        if self.issued_on and self.expires_on:
            return Interval(start=self.issued_on, end=self.expires_on)
        return None

    def is_valid_at(self, day: date) -> bool | None:
        """Tri-state: True, False, or None when the document's dates are unknown.

        None matters. An unknown expiry is not a passing constraint — it routes the
        node to `needs_human_review` rather than silently succeeding.
        """
        if self.expires_on is None:
            return None
        if self.issued_on and day < self.issued_on:
            return False
        return day <= self.expires_on

    def age_days_at(self, day: date) -> int | None:
        """How old the document is on `day`, for max-age rules like the civil extract."""
        if self.issued_on is None:
            return None
        return (day - self.issued_on).days

    @property
    def is_provisional(self) -> bool:
        return self.verified_by == VerificationSource.EXTRACTED


class Applicant(BaseModel):
    applicant_id: str
    display_name: str | None = None
    nationality_status: NationalityStatus
    residence_country: str
    documents: list[IdentityDocument] = Field(default_factory=list)

    def documents_of(self, kind: DocumentKind) -> list[IdentityDocument]:
        return [d for d in self.documents if d.kind == kind]

    def best_document(self, kind: DocumentKind) -> IdentityDocument | None:
        """The document of this kind that survives longest.

        When an applicant holds several — an expired travel document and its renewal —
        constraints should be evaluated against the most favourable one, so that a plan
        is not declared infeasible on the strength of a superseded document.
        """
        candidates = self.documents_of(kind)
        if not candidates:
            return None
        dated = [d for d in candidates if d.expires_on is not None]
        if not dated:
            return candidates[0]
        return max(dated, key=lambda d: d.expires_on)  # type: ignore[arg-type,return-value]

    def holds(self, kind: DocumentKind) -> bool:
        return bool(self.documents_of(kind))
