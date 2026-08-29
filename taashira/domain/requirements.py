"""Requirements and the versioned packs that declare them.

Packs are *data*. A corridor is a YAML file, not a code path, so supporting a new
route is authoring a file rather than editing the planner. Every requirement carries
an `authority` citation; the adversarial critic may only raise findings that cite one
of these ids, which is what stops it inventing visa rules.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from taashira.domain.constraints import TemporalConstraint
from taashira.domain.documents import DocumentKind, NationalityStatus


class Actor(StrEnum):
    """Who has to move for this requirement to be satisfied.

    Drives what the agent can actually do about it: chase the applicant, draft a
    request to an institution, or produce the artefact itself.
    """

    APPLICANT = "applicant"  # the applicant must do something in person
    INSTITUTION = "institution"  # a university, bank or sponsor must issue something
    AUTHORITY = "authority"  # a government body, on its own timetable
    AGENT = "agent"  # Taashira can produce this itself


class Applicability(BaseModel):
    """When a requirement enters the graph at all.

    A national with an ordinary passport and a stateless holder of a refugee travel
    document walk different paths through the same corridor; this is where they fork.
    """

    nationality_status: list[NationalityStatus] | None = None
    holds_document: list[DocumentKind] | None = None
    lacks_document: list[DocumentKind] | None = None

    def matches(self, status: NationalityStatus, held: set[DocumentKind]) -> bool:
        if self.nationality_status and status not in self.nationality_status:
            return False
        if self.holds_document and not all(d in held for d in self.holds_document):
            return False
        return not (self.lacks_document and any(d in held for d in self.lacks_document))


class WaitTimeSignal(BaseModel):
    """Binds a requirement's lead time to a published consular wait time.

    Only the published figure is read — never the booking system itself.
    """

    post: str = Field(description="Consular post as it appears in the published table.")
    visa_class: str = "student"


class Requirement(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    actor: Actor
    authority: str = Field(
        min_length=1,
        description="Citation for the rule this encodes. The critic may only cite these.",
    )

    produces: DocumentKind | None = None
    depends_on: list[str] = Field(default_factory=list)

    lead_time_p50_days: int = Field(ge=0)
    lead_time_p90_days: int = Field(ge=0)

    constraints: list[TemporalConstraint] = Field(default_factory=list)
    applies_when: Applicability | None = None

    remediation_only: bool = Field(
        default=False,
        description=(
            "Not part of the base graph. Enters only when a failing constraint "
            "names it as a remediation — e.g. renewing a travel document."
        ),
    )
    optional: bool = False
    guidance: str | None = None
    wait_time_signal: WaitTimeSignal | None = Field(
        default=None,
        description="When set, a live observation supersedes this requirement's lead estimate.",
    )

    @model_validator(mode="after")
    def _lead_times_ordered(self) -> Requirement:
        if self.lead_time_p90_days < self.lead_time_p50_days:
            raise ValueError(
                f"{self.id}: p90 lead time {self.lead_time_p90_days} "
                f"is below p50 {self.lead_time_p50_days}"
            )
        return self


class Corridor(BaseModel):
    """One (document context → destination + visa type) route."""

    id: str = Field(pattern=r"^[a-z0-9-]+__[a-z0-9-]+$")
    origin_label: str
    destination_label: str
    visa_type: str

    def __str__(self) -> str:
        return f"{self.origin_label} → {self.destination_label} {self.visa_type}"


class RequirementPack(BaseModel):
    pack_id: str
    version: str
    corridor: Corridor
    requirements: list[Requirement]
    sources: list[str] = Field(
        default_factory=list,
        description="Where these rules came from. Curated by hand, never scraped or generated.",
    )

    @model_validator(mode="after")
    def _referential_integrity(self) -> RequirementPack:
        ids = {r.id for r in self.requirements}
        if len(ids) != len(self.requirements):
            raise ValueError(f"{self.pack_id}: duplicate requirement ids")

        for req in self.requirements:
            for dep in req.depends_on:
                if dep not in ids:
                    raise ValueError(f"{req.id} depends on unknown requirement '{dep}'")
            for constraint in req.constraints:
                remediation = constraint.remediation
                if remediation and remediation not in ids:
                    raise ValueError(
                        f"{req.id}: constraint names unknown remediation '{remediation}'"
                    )
        return self

    def by_id(self, requirement_id: str) -> Requirement:
        for req in self.requirements:
            if req.id == requirement_id:
                return req
        raise KeyError(f"no requirement '{requirement_id}' in pack {self.pack_id}")

    @property
    def authorities(self) -> set[str]:
        """Every citation the critic is permitted to reference."""
        return {r.authority for r in self.requirements}
