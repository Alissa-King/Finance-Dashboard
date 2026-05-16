"""
Seed script — populates a few funders, grants, and requirements so you can
verify the schema and test the UI before importing real data.

Usage:
  python seed.py
"""
from datetime import date

from src.db import get_session
from src.models import Deadline, Funder, FunderType, Grant, ReportFrequency, ReportingRequirement, Staff
from src.services.instance_generator import generate_deadlines


def generate_missing_deadlines() -> int:
    """Generate deadlines for any grant/requirement pairs that have none. Returns count added."""
    added = 0
    with get_session() as session:
        grants = session.query(Grant).all()
        requirements = session.query(ReportingRequirement).all()
        existing = {(d.grant_id, d.requirement_id) for d in session.query(Deadline).all()}
        for grant in grants:
            funder_reqs = [r for r in requirements if r.funder_id == grant.funder_id]
            for req in funder_reqs:
                if (grant.id, req.id) not in existing:
                    for deadline in generate_deadlines(grant, req):
                        session.add(deadline)
                        added += 1
    return added


def seed():
    with get_session() as session:
        if session.query(Funder).count() > 0:
            added = generate_missing_deadlines()
            print(f"Funders already exist — generated {added} missing deadlines.")
            return

        # Staff
        director = Staff(name="Finance Director", email="finance@yourorg.org", role="admin")
        session.add(director)

        # Funders
        hrsa = Funder(name="HRSA", type=FunderType.federal, parent_agency="HHS",
                      website="https://www.hrsa.gov", organization_id=1)
        oha = Funder(name="Oregon Health Authority", type=FunderType.state,
                     website="https://www.oregon.gov/oha", organization_id=1)
        measure110 = Funder(name="Measure 110/BHRD", type=FunderType.state, organization_id=1)
        session.add_all([hrsa, oha, measure110])
        session.flush()

        # Grants
        ryan_white = Grant(
            organization_id=1,
            funder_id=hrsa.id,
            grant_name="Ryan White Part B",
            award_number="H89HA00001",
            program="Ryan White Part B",
            period_start=date(2025, 4, 1),
            period_end=date(2026, 3, 31),
            award_amount=500000.00,
            program_officer_name="Jane Smith",
            program_officer_email="jane.smith@hrsa.gov",
        )
        oha_grant = Grant(
            organization_id=1,
            funder_id=oha.id,
            grant_name="OHA HIV Prevention",
            period_start=date(2025, 7, 1),
            period_end=date(2026, 6, 30),
            award_amount=150000.00,
        )
        session.add_all([ryan_white, oha_grant])
        session.flush()

        # Reporting requirements
        sf425 = ReportingRequirement(
            funder_id=hrsa.id,
            name="SF-425 Federal Financial Report",
            frequency=ReportFrequency.quarterly,
            due_offset_days=30,
            submission_method="HRSA EHBs portal",
            description="Federal financial report required for all HRSA grants",
        )
        program_report = ReportingRequirement(
            funder_id=hrsa.id,
            name="Ryan White Program Report",
            frequency=ReportFrequency.annual,
            due_offset_days=90,
            submission_method="HRSA EHBs portal",
        )
        oha_financial = ReportingRequirement(
            funder_id=oha.id,
            name="OHA Financial Status Report",
            frequency=ReportFrequency.semi_annual,
            due_offset_days=30,
            submission_method="Email to program officer",
        )
        session.add_all([sf425, program_report, oha_financial])
        session.flush()

        # Generate deadline instances for each grant/requirement pair
        for grant, req in [
            (ryan_white, sf425),
            (ryan_white, program_report),
            (oha_grant, oha_financial),
        ]:
            for deadline in generate_deadlines(grant, req):
                session.add(deadline)

        from src.models import Deadline
        print("Seed complete:")
        print(f"  Funders: {session.query(Funder).count()}")
        print(f"  Grants:  {session.query(Grant).count()}")
        print(f"  Requirements: {session.query(ReportingRequirement).count()}")
        print(f"  Deadlines: {session.query(Deadline).count()}")


if __name__ == "__main__":
    seed()
