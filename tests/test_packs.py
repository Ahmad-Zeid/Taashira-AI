"""Pack tests.

Packs are the only place visa rules live, and they are hand-curated. These tests guard
the properties that make that safe: every pack parses, every reference resolves, and
every rule carries a citation the critic can be held to.
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from taashira.domain.requirements import RequirementPack
from taashira.packs import available_packs, load_pack_by_id

ALL_PACKS = available_packs()


def test_at_least_one_pack_ships():
    assert ALL_PACKS


@pytest.mark.parametrize("pack_id", ALL_PACKS)
def test_pack_parses_and_validates(pack_id):
    pack = load_pack_by_id(pack_id)
    assert pack.pack_id == pack_id
    assert pack.requirements


@pytest.mark.parametrize("pack_id", ALL_PACKS)
def test_every_requirement_carries_a_citation(pack_id):
    """The critic may only raise findings citing one of these, so none may be blank."""
    for requirement in load_pack_by_id(pack_id).requirements:
        assert requirement.authority.strip(), f"{requirement.id} has no authority"


@pytest.mark.parametrize("pack_id", ALL_PACKS)
def test_pack_records_where_its_rules_came_from(pack_id):
    assert load_pack_by_id(pack_id).sources, "packs must cite their sources"


@pytest.mark.parametrize("pack_id", ALL_PACKS)
def test_remediation_targets_are_remediation_only(pack_id):
    """A node spliced in as a remedy must not also sit in the base graph.

    Otherwise it would appear for every applicant, cascade or not, and the graph would
    stop being a function of the applicant's actual documents.
    """
    pack = load_pack_by_id(pack_id)
    for requirement in pack.requirements:
        for constraint in requirement.constraints:
            if constraint.remediation:
                target = pack.by_id(constraint.remediation)
                assert target.remediation_only, (
                    f"{target.id} is a remediation target but sits in the base graph"
                )


def test_unknown_remediation_is_rejected():
    """Referential integrity is enforced at parse time, not discovered at runtime."""
    raw = yaml.safe_load("""
pack_id: broken
version: "0.0.1"
corridor:
  id: aa-bb__cc-dd
  origin_label: A
  destination_label: B
  visa_type: X
requirements:
  - id: only_node
    label: Only
    actor: applicant
    authority: "test"
    lead_time_p50_days: 1
    lead_time_p90_days: 2
    constraints:
      - kind: valid_at
        document: passport
        at: today
        remediation: does_not_exist
""")
    with pytest.raises(ValidationError, match="unknown remediation"):
        RequirementPack.model_validate(raw)


def test_unknown_dependency_is_rejected():
    raw = yaml.safe_load("""
pack_id: broken
version: "0.0.1"
corridor:
  id: aa-bb__cc-dd
  origin_label: A
  destination_label: B
  visa_type: X
requirements:
  - id: only_node
    label: Only
    actor: applicant
    authority: "test"
    depends_on: [ghost]
    lead_time_p50_days: 1
    lead_time_p90_days: 2
""")
    with pytest.raises(ValidationError, match="unknown requirement"):
        RequirementPack.model_validate(raw)


def test_inverted_lead_times_are_rejected():
    raw = yaml.safe_load("""
pack_id: broken
version: "0.0.1"
corridor:
  id: aa-bb__cc-dd
  origin_label: A
  destination_label: B
  visa_type: X
requirements:
  - id: only_node
    label: Only
    actor: applicant
    authority: "test"
    lead_time_p50_days: 30
    lead_time_p90_days: 5
""")
    with pytest.raises(ValidationError, match="below p50"):
        RequirementPack.model_validate(raw)
