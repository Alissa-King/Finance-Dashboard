"""
CSV importer for existing compliance calendars.

Expected columns (case-insensitive, extra columns ignored):
  grant_name, funder_name, funder_type, requirement_name, frequency,
  due_date (YYYY-MM-DD), fiscal_period_covered, status, notes
"""
import pandas as pd
from datetime import date, datetime

from src.models import (
    Deadline, DeadlineStatus, Funder, FunderType, Grant,
    ReportFrequency, ReportingRequirement,
)
from src.db import get_session


def _coerce_status(raw: str) -> DeadlineStatus:
    mapping = {
        "not started": DeadlineStatus.not_started,
        "in progress": DeadlineStatus.in_progress,
        "submitted": DeadlineStatus.submitted,
        "accepted": DeadlineStatus.accepted,
        "closed": DeadlineStatus.closed,
        "overdue": DeadlineStatus.overdue,
    }
    return mapping.get(str(raw).strip().lower(), DeadlineStatus.not_started)


def _coerce_frequency(raw: str) -> ReportFrequency:
    mapping = {
        "monthly": ReportFrequency.monthly,
        "quarterly": ReportFrequency.quarterly,
        "semi-annual": ReportFrequency.semi_annual,
        "semi_annual": ReportFrequency.semi_annual,
        "annual": ReportFrequency.annual,
        "one-time": ReportFrequency.one_time,
        "one_time": ReportFrequency.one_time,
    }
    return mapping.get(str(raw).strip().lower(), ReportFrequency.one_time)


def import_csv(filepath: str, organization_id: int = 1) -> dict:
    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"grant_name", "funder_name", "requirement_name", "due_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    stats = {"funders": 0, "grants": 0, "requirements": 0, "deadlines": 0, "errors": []}

    with get_session() as session:
        funder_cache: dict[str, Funder] = {}
        grant_cache: dict[str, Grant] = {}
        req_cache: dict[str, ReportingRequirement] = {}

        for _, row in df.iterrows():
            try:
                # Funder
                funder_name = str(row["funder_name"]).strip()
                if funder_name not in funder_cache:
                    funder = session.query(Funder).filter_by(name=funder_name, organization_id=organization_id).first()
                    if not funder:
                        ftype = FunderType.other
                        if "funder_type" in df.columns:
                            ftype_raw = str(row.get("funder_type", "other")).strip().lower().replace(" ", "_")
                            ftype = FunderType(ftype_raw) if ftype_raw in FunderType._value2member_map_ else FunderType.other
                        funder = Funder(name=funder_name, type=ftype, organization_id=organization_id)
                        session.add(funder)
                        session.flush()
                        stats["funders"] += 1
                    funder_cache[funder_name] = funder

                funder = funder_cache[funder_name]

                # Grant
                grant_name = str(row["grant_name"]).strip()
                grant_key = f"{funder_name}::{grant_name}"
                if grant_key not in grant_cache:
                    grant = session.query(Grant).filter_by(grant_name=grant_name, funder_id=funder.id).first()
                    if not grant:
                        grant = Grant(
                            organization_id=organization_id,
                            funder_id=funder.id,
                            grant_name=grant_name,
                            period_start=date.today().replace(month=1, day=1),
                            period_end=date.today().replace(month=12, day=31),
                        )
                        session.add(grant)
                        session.flush()
                        stats["grants"] += 1
                    grant_cache[grant_key] = grant

                grant = grant_cache[grant_key]

                # Requirement
                req_name = str(row["requirement_name"]).strip()
                req_key = f"{funder.id}::{req_name}"
                if req_key not in req_cache:
                    req = session.query(ReportingRequirement).filter_by(name=req_name, funder_id=funder.id).first()
                    if not req:
                        freq = ReportFrequency.one_time
                        if "frequency" in df.columns:
                            freq = _coerce_frequency(row.get("frequency", "one_time"))
                        req = ReportingRequirement(funder_id=funder.id, name=req_name, frequency=freq)
                        session.add(req)
                        session.flush()
                        stats["requirements"] += 1
                    req_cache[req_key] = req

                req = req_cache[req_key]

                # Deadline
                due_date = pd.to_datetime(row["due_date"]).date()
                status = _coerce_status(row.get("status", "not_started"))
                fiscal_period = str(row.get("fiscal_period_covered", "")).strip() or None
                notes = str(row.get("notes", "")).strip() or None

                deadline = Deadline(
                    organization_id=organization_id,
                    grant_id=grant.id,
                    requirement_id=req.id,
                    due_date=due_date,
                    fiscal_period_covered=fiscal_period,
                    status=status,
                    notes=notes,
                )
                session.add(deadline)
                stats["deadlines"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {_ + 2}: {e}")

    return stats
