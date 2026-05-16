"""
Seed script — populates funders, grants, requirements, and deadlines.

Usage:
  python seed.py            # gentle seed (skips if data exists)
  python seed.py --demo     # wipe + load rich demo data
"""
from datetime import date, timedelta

from src.db import get_session
from src.models import (
    AuditLog, Deadline, DeadlineStatus, Funder, FunderType,
    Grant, ReportFrequency, ReportingRequirement, Staff,
)
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


def seed_demo() -> int:
    """
    Wipe all data and insert rich demo deadlines anchored to today.
    Designed to make every dashboard element show interesting data:
      - 3 overdue (red ticker + glowing KPI card)
      - 2 due within 7 days (amber)
      - 2 more due within 30 days
      - 7 submitted / accepted (~50% compliance → amber gauge)
      - 6 future not-started
    """
    today = date.today()

    with get_session() as session:
        # Clear in FK order
        session.query(AuditLog).delete()
        session.query(Deadline).delete()
        session.query(ReportingRequirement).delete()
        session.query(Grant).delete()
        session.query(Staff).delete()
        session.query(Funder).delete()
        session.flush()

        # ── Staff ──────────────────────────────────────────────────────────
        director = Staff(name="Finance Director", email="finance@hivalliance.org", role="admin")
        analyst  = Staff(name="Grants Analyst",   email="grants@hivalliance.org",  role="analyst")
        session.add_all([director, analyst])
        session.flush()

        # ── Funders ────────────────────────────────────────────────────────
        hrsa = Funder(name="HRSA", type=FunderType.federal, parent_agency="HHS",
                      website="https://www.hrsa.gov", organization_id=1)
        oha  = Funder(name="Oregon Health Authority", type=FunderType.state,
                      website="https://www.oregon.gov/oha", organization_id=1)
        m110 = Funder(name="Measure 110/BHRD", type=FunderType.state,
                      website="https://www.oregon.gov/oha/ph/preventionwellness/pages/measure110.aspx",
                      organization_id=1)
        hecc = Funder(name="HECC", type=FunderType.state, parent_agency="Oregon HECC",
                      website="https://www.oregon.gov/highered", organization_id=1)
        session.add_all([hrsa, oha, m110, hecc])
        session.flush()

        # ── Grants ─────────────────────────────────────────────────────────
        rw = Grant(
            organization_id=1, funder_id=hrsa.id,
            grant_name="Ryan White Part B", award_number="H89HA00001",
            program="Ryan White Part B",
            period_start=date(today.year - 1, 4, 1),
            period_end=date(today.year, 3, 31),
            award_amount=500_000.00,
            program_officer_name="Jane Smith",
            program_officer_email="jane.smith@hrsa.gov",
        )
        oha_g = Grant(
            organization_id=1, funder_id=oha.id,
            grant_name="OHA HIV Prevention",
            period_start=date(today.year - 1, 7, 1),
            period_end=date(today.year, 6, 30),
            award_amount=150_000.00,
        )
        m110_g = Grant(
            organization_id=1, funder_id=m110.id,
            grant_name="Measure 110 Behavioral Health",
            period_start=date(today.year - 1, 7, 1),
            period_end=date(today.year, 6, 30),
            award_amount=200_000.00,
        )
        hecc_g = Grant(
            organization_id=1, funder_id=hecc.id,
            grant_name="HECC Navigator Program",
            period_start=date(today.year - 1, 9, 1),
            period_end=date(today.year, 8, 31),
            award_amount=75_000.00,
        )
        session.add_all([rw, oha_g, m110_g, hecc_g])
        session.flush()

        # ── Reporting requirements ─────────────────────────────────────────
        sf425 = ReportingRequirement(
            funder_id=hrsa.id, name="SF-425 Federal Financial Report",
            frequency=ReportFrequency.quarterly, due_offset_days=30,
            submission_method="HRSA EHBs portal",
            description="Federal financial report required for all HRSA grants",
        )
        rw_prog = ReportingRequirement(
            funder_id=hrsa.id, name="Ryan White Program Report",
            frequency=ReportFrequency.annual, due_offset_days=90,
            submission_method="HRSA EHBs portal",
        )
        oha_fsr = ReportingRequirement(
            funder_id=oha.id, name="OHA Financial Status Report",
            frequency=ReportFrequency.semi_annual, due_offset_days=30,
            submission_method="Email to program officer",
        )
        m110_q = ReportingRequirement(
            funder_id=m110.id, name="M110 Quarterly Progress Report",
            frequency=ReportFrequency.quarterly, due_offset_days=30,
            submission_method="BHRD online portal",
            description="Quarterly participant data and expenditure report",
        )
        m110_a = ReportingRequirement(
            funder_id=m110.id, name="M110 Annual Outcomes Report",
            frequency=ReportFrequency.annual, due_offset_days=60,
            submission_method="BHRD online portal",
        )
        hecc_fin = ReportingRequirement(
            funder_id=hecc.id, name="HECC Financial Report",
            frequency=ReportFrequency.semi_annual, due_offset_days=30,
            submission_method="HECC grants portal",
        )
        hecc_prog = ReportingRequirement(
            funder_id=hecc.id, name="HECC Program Progress Report",
            frequency=ReportFrequency.annual, due_offset_days=45,
            submission_method="HECC grants portal",
        )
        session.add_all([sf425, rw_prog, oha_fsr, m110_q, m110_a, hecc_fin, hecc_prog])
        session.flush()

        # ── Deadlines ──────────────────────────────────────────────────────
        # (grant, req, fiscal_period, days_from_today, status, days_submitted_before_due)
        specs = [
            # Accepted — completed in the past, on time
            (rw,     sf425,    "Q3 FY2025",  -290, "Accepted",    3),
            (rw,     sf425,    "Q4 FY2025",  -200, "Accepted",    5),
            (m110_g, m110_q,   "Q3 FY2025",  -200, "Accepted",    2),
            (hecc_g, hecc_fin, "H2 FY2025",  -190, "Accepted",    4),
            # Submitted — recent past, on time
            (rw,     sf425,    "Q1 FY2026",  -105, "Submitted",   1),
            (oha_g,  oha_fsr,  "H2 FY2025",  -105, "Submitted",   7),
            (m110_g, m110_q,   "Q4 FY2025",  -105, "Submitted",   3),
            # Overdue — missed, showing red in ticker and KPI
            (hecc_g, hecc_prog,"FY2025",      -45, "Overdue",     None),
            (rw,     sf425,    "Q2 FY2026",   -16, "Overdue",     None),
            (m110_g, m110_q,   "Q1 FY2026",   -16, "Overdue",     None),
            # Due in next 7 days — urgent, amber
            (oha_g,  oha_fsr,  "H1 FY2026",    4, "In Progress", None),
            (hecc_g, hecc_fin, "H1 FY2026",    6, "In Progress", None),
            # Due in 8–30 days — plan ahead, cyan
            (rw,     rw_prog,  "FY2025",       22, "Not Started", None),
            (m110_g, m110_q,   "Q2 FY2026",    27, "Not Started", None),
            # Future — not started
            (m110_g, m110_a,   "FY2026",      105, "Not Started", None),
            (rw,     sf425,    "Q3 FY2026",   135, "Not Started", None),
            (oha_g,  oha_fsr,  "H2 FY2026",   180, "Not Started", None),
            (hecc_g, hecc_prog,"FY2026",       200, "Not Started", None),
        ]

        for g, r, period, days, status_val, sub_days in specs:
            due       = today + timedelta(days=days)
            submitted = (due - timedelta(days=sub_days)) if sub_days is not None else None
            session.add(Deadline(
                organization_id=1,
                grant_id=g.id,
                requirement_id=r.id,
                due_date=due,
                fiscal_period_covered=period,
                status=DeadlineStatus(status_val),
                submitted_date=submitted,
            ))

        return len(specs)


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
        measure110 = Funder(name="Measure 110/BHRD", type=FunderType.state,
                            website="https://www.oregon.gov/oha/ph/preventionwellness/pages/measure110.aspx",
                            organization_id=1)
        hecc = Funder(name="HECC", type=FunderType.state, parent_agency="Oregon HECC",
                      website="https://www.oregon.gov/highered", organization_id=1)
        session.add_all([hrsa, oha, measure110, hecc])
        session.flush()

        # Grants
        ryan_white = Grant(
            organization_id=1, funder_id=hrsa.id,
            grant_name="Ryan White Part B", award_number="H89HA00001",
            program="Ryan White Part B",
            period_start=date(2025, 4, 1), period_end=date(2026, 3, 31),
            award_amount=500_000.00,
            program_officer_name="Jane Smith",
            program_officer_email="jane.smith@hrsa.gov",
        )
        oha_grant = Grant(
            organization_id=1, funder_id=oha.id,
            grant_name="OHA HIV Prevention",
            period_start=date(2025, 7, 1), period_end=date(2026, 6, 30),
            award_amount=150_000.00,
        )
        m110_grant = Grant(
            organization_id=1, funder_id=measure110.id,
            grant_name="Measure 110 Behavioral Health",
            period_start=date(2025, 7, 1), period_end=date(2026, 6, 30),
            award_amount=200_000.00,
        )
        hecc_grant = Grant(
            organization_id=1, funder_id=hecc.id,
            grant_name="HECC Navigator Program",
            period_start=date(2025, 9, 1), period_end=date(2026, 8, 31),
            award_amount=75_000.00,
        )
        session.add_all([ryan_white, oha_grant, m110_grant, hecc_grant])
        session.flush()

        # Reporting requirements
        sf425 = ReportingRequirement(
            funder_id=hrsa.id, name="SF-425 Federal Financial Report",
            frequency=ReportFrequency.quarterly, due_offset_days=30,
            submission_method="HRSA EHBs portal",
            description="Federal financial report required for all HRSA grants",
        )
        program_report = ReportingRequirement(
            funder_id=hrsa.id, name="Ryan White Program Report",
            frequency=ReportFrequency.annual, due_offset_days=90,
            submission_method="HRSA EHBs portal",
        )
        oha_financial = ReportingRequirement(
            funder_id=oha.id, name="OHA Financial Status Report",
            frequency=ReportFrequency.semi_annual, due_offset_days=30,
            submission_method="Email to program officer",
        )
        m110_quarterly = ReportingRequirement(
            funder_id=measure110.id, name="M110 Quarterly Progress Report",
            frequency=ReportFrequency.quarterly, due_offset_days=30,
            submission_method="BHRD online portal",
            description="Quarterly participant data and expenditure report",
        )
        m110_annual = ReportingRequirement(
            funder_id=measure110.id, name="M110 Annual Outcomes Report",
            frequency=ReportFrequency.annual, due_offset_days=60,
            submission_method="BHRD online portal",
        )
        hecc_financial = ReportingRequirement(
            funder_id=hecc.id, name="HECC Financial Report",
            frequency=ReportFrequency.semi_annual, due_offset_days=30,
            submission_method="HECC grants portal",
        )
        hecc_program = ReportingRequirement(
            funder_id=hecc.id, name="HECC Program Progress Report",
            frequency=ReportFrequency.annual, due_offset_days=45,
            submission_method="HECC grants portal",
        )
        session.add_all([sf425, program_report, oha_financial, m110_quarterly, m110_annual,
                         hecc_financial, hecc_program])
        session.flush()

        for grant, req in [
            (ryan_white, sf425), (ryan_white, program_report),
            (oha_grant, oha_financial),
            (m110_grant, m110_quarterly), (m110_grant, m110_annual),
            (hecc_grant, hecc_financial), (hecc_grant, hecc_program),
        ]:
            for deadline in generate_deadlines(grant, req):
                session.add(deadline)

        print("Seed complete:")
        print(f"  Funders:      {session.query(Funder).count()}")
        print(f"  Grants:       {session.query(Grant).count()}")
        print(f"  Requirements: {session.query(ReportingRequirement).count()}")
        print(f"  Deadlines:    {session.query(Deadline).count()}")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        n = seed_demo()
        print(f"Demo seed complete: {n} deadlines loaded.")
    else:
        seed()
