"""Synthetic applicants for local development, tests, and the demo.

SYNTHETIC ONLY. No real identity documents, numbers, or personal data appear here or
anywhere in this repository. The dates are chosen to exercise the cascade the product
exists to handle, not to describe any actual person.
"""

from __future__ import annotations

from datetime import date

from taashira.domain.documents import (
    Applicant,
    DocumentKind,
    IdentityDocument,
    NationalityStatus,
    VerificationSource,
)
from taashira.domain.temporal import Interval

#: A two-year masters programme starting in the January intake.
MASTERS_PROGRAM = Interval(start=date(2027, 1, 10), end=date(2028, 12, 20))

#: The day the reference plans are computed from.
REFERENCE_TODAY = date(2026, 8, 27)


def stateless_masters_applicant() -> Applicant:
    """Holder of a one-year refugee travel document applying for a two-year masters.

    Every value below is chosen to make the cascade fire:

    * the travel document expires 2027-03-01, so it cannot cover a programme ending
      2028-12-20 — which splices in a renewal;
    * the renewal needs a civil extract issued within three years, and this one was
      issued 2023-06-15, so it is already stale — which splices in a re-issue.

    Three levels, all from the pack rather than from code.
    """
    return Applicant(
        applicant_id="apl_demo_0001",
        display_name="Synthetic Applicant",
        nationality_status=NationalityStatus.REFUGEE_TRAVEL_DOCUMENT,
        residence_country="LB",
        documents=[
            IdentityDocument(
                kind=DocumentKind.TRAVEL_DOCUMENT,
                issuer="Lebanon — General Security",
                issued_on=date(2026, 3, 1),
                expires_on=date(2027, 3, 1),  # one year: no UNRWA vitality card on file
                reference_redacted="••••4192",
                extraction_confidence=0.94,
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
            IdentityDocument(
                kind=DocumentKind.UNRWA_REGISTRATION,
                issuer="UNRWA",
                issued_on=date(2019, 4, 2),
                expires_on=date(2029, 4, 2),
                extraction_confidence=0.91,
            ),
            IdentityDocument(
                kind=DocumentKind.CIVIL_EXTRACT,
                issuer="Lebanon — General Security",
                issued_on=date(2023, 6, 15),  # stale: over three years by renewal time
                expires_on=date(2033, 6, 15),
                extraction_confidence=0.88,
            ),
            IdentityDocument(
                kind=DocumentKind.ADMISSION_LETTER,
                issuer="Synthetic University",
                issued_on=date(2026, 8, 1),
                expires_on=date(2027, 1, 10),
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
            IdentityDocument(
                kind=DocumentKind.FINANCIAL_STATEMENT,
                issuer="Synthetic Bank",
                issued_on=date(2026, 8, 20),  # recent, but seasons in time for the interview
                expires_on=date(2027, 8, 20),
                extraction_confidence=0.79,
            ),
        ],
    )


def well_documented_applicant() -> Applicant:
    """Control case: an ordinary passport that comfortably outlives the programme.

    Used to prove the cascade is driven by the constraints rather than hardcoded —
    the same pack produces a graph with no remediation nodes at all.
    """
    return Applicant(
        applicant_id="apl_demo_0002",
        display_name="Synthetic Control",
        nationality_status=NationalityStatus.NATIONAL,
        residence_country="LB",
        documents=[
            IdentityDocument(
                kind=DocumentKind.PASSPORT,
                issuer="Synthetic Republic",
                issued_on=date(2024, 1, 1),
                expires_on=date(2034, 1, 1),
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
            IdentityDocument(
                kind=DocumentKind.TRAVEL_DOCUMENT,
                issuer="Synthetic Republic",
                issued_on=date(2024, 1, 1),
                expires_on=date(2034, 1, 1),
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
            IdentityDocument(
                kind=DocumentKind.ADMISSION_LETTER,
                issuer="Synthetic University",
                issued_on=date(2026, 8, 1),
                expires_on=date(2027, 1, 10),
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
            IdentityDocument(
                kind=DocumentKind.FINANCIAL_STATEMENT,
                issuer="Synthetic Bank",
                issued_on=date(2025, 1, 5),  # well seasoned
                expires_on=date(2027, 1, 5),
                verified_by=VerificationSource.USER_CONFIRMED,
            ),
        ],
    )
