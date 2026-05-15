from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from src.models import Deadline, DeadlineStatus, Grant, ReportingRequirement, ReportFrequency


def _quarter_periods(start: date, end: date):
    """Yield (period_label, period_end) for each quarter in [start, end]."""
    cursor = date(start.year, ((start.month - 1) // 3) * 3 + 1, 1)
    while cursor <= end:
        q_end = cursor + relativedelta(months=3) - timedelta(days=1)
        q_num = (cursor.month - 1) // 3 + 1
        label = f"Q{q_num} FY{cursor.year if cursor.month >= 7 else cursor.year}"
        yield label, min(q_end, end)
        cursor += relativedelta(months=3)


def _semi_annual_periods(start: date, end: date):
    cursor = date(start.year, ((start.month - 1) // 6) * 6 + 1, 1)
    while cursor <= end:
        p_end = cursor + relativedelta(months=6) - timedelta(days=1)
        half = "H1" if cursor.month <= 6 else "H2"
        label = f"{half} FY{cursor.year}"
        yield label, min(p_end, end)
        cursor += relativedelta(months=6)


def _monthly_periods(start: date, end: date):
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        p_end = cursor + relativedelta(months=1) - timedelta(days=1)
        label = cursor.strftime("%b %Y")
        yield label, min(p_end, end)
        cursor += relativedelta(months=1)


def _annual_periods(start: date, end: date):
    cursor = date(start.year, start.month, start.day)
    while cursor <= end:
        p_end = cursor + relativedelta(years=1) - timedelta(days=1)
        label = f"FY{cursor.year}"
        yield label, min(p_end, end)
        cursor += relativedelta(years=1)


def generate_deadlines(
    grant: Grant,
    requirement: ReportingRequirement,
    organization_id: int = 1,
) -> list[Deadline]:
    """
    Given a grant and a reporting requirement, generate all deadline instances
    covering the grant's award period.
    """
    start = grant.period_start
    end = grant.period_end
    offset = requirement.due_offset_days

    if requirement.frequency == ReportFrequency.quarterly:
        periods = list(_quarter_periods(start, end))
    elif requirement.frequency == ReportFrequency.semi_annual:
        periods = list(_semi_annual_periods(start, end))
    elif requirement.frequency == ReportFrequency.monthly:
        periods = list(_monthly_periods(start, end))
    elif requirement.frequency == ReportFrequency.annual:
        periods = list(_annual_periods(start, end))
    elif requirement.frequency == ReportFrequency.one_time:
        periods = [(f"FY{end.year}", end)]
    else:
        periods = []

    deadlines = []
    for label, period_end in periods:
        due = period_end + timedelta(days=offset)
        deadlines.append(
            Deadline(
                organization_id=organization_id,
                grant_id=grant.id,
                requirement_id=requirement.id,
                due_date=due,
                fiscal_period_covered=label,
                status=DeadlineStatus.not_started,
            )
        )
    return deadlines
