"""Seed or reset the demo campaign.

Run between demo takes. Writes the applicant *and* the campaign, so document ingestion
has a dossier to update.

The seeded applicant deliberately has **no travel document**: the demo begins with an
incomplete dossier, and uploading the document is what makes the cascade appear on camera.
"""

from __future__ import annotations

import argparse
from datetime import date

from taashira.config import Settings
from taashira.domain.documents import DocumentKind
from taashira.fixtures import MASTERS_PROGRAM, stateless_masters_applicant
from taashira.packs import load_pack_by_id
from taashira.service import replan
from taashira.signals import observed_lead_days
from taashira.store import build_store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="taashira-506919")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument(
        "--with-travel-document",
        action="store_true",
        help="Seed with the travel document already on file (skips the upload beat).",
    )
    args = parser.parse_args()

    config = Settings(project_id=args.project)
    store = build_store(config)
    pack = load_pack_by_id("lb-prtd__us-f1")

    applicant = stateless_masters_applicant()
    if not args.with_travel_document:
        applicant.documents = [
            d for d in applicant.documents if d.kind is not DocumentKind.TRAVEL_DOCUMENT
        ]

    store.save_applicant(applicant)
    result = replan(
        store=store,
        pack=pack,
        applicant=applicant,
        program=MASTERS_PROGRAM,
        today=date.fromisoformat(args.today),
        observed_lead_days=observed_lead_days(pack),
    )

    campaign = result.campaign
    print(f"campaign   : {campaign.campaign_id} (v{campaign.version})")
    print(f"applicant  : {applicant.applicant_id}, {len(applicant.documents)} documents on file")
    print(f"feasible   : {campaign.feasible}")
    print(f"nodes      : {len(campaign.nodes)}")
    print(f"cascade    : {[n.requirement_id for n in campaign.spliced_nodes] or 'none yet'}")
    print(f"binding    : {campaign.binding_constraint}")
    if not args.with_travel_document:
        print("\nNo travel document on file. Upload one to trigger the cascade.")


if __name__ == "__main__":
    main()
