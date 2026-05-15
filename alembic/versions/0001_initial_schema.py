"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "funders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.Enum("federal", "state", "local", "private_foundation", "other", name="fundertype"), nullable=False),
        sa.Column("parent_agency", sa.String(255)),
        sa.Column("website", sa.String(500)),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(100)),
    )

    op.create_table(
        "grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("funder_id", sa.Integer(), sa.ForeignKey("funders.id"), nullable=False),
        sa.Column("grant_name", sa.String(255), nullable=False),
        sa.Column("award_number", sa.String(100)),
        sa.Column("program", sa.String(255)),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("award_amount", sa.Numeric(15, 2)),
        sa.Column("program_officer_name", sa.String(255)),
        sa.Column("program_officer_email", sa.String(255)),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "reporting_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("funder_id", sa.Integer(), sa.ForeignKey("funders.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("frequency", sa.Enum("monthly", "quarterly", "semi_annual", "annual", "one_time", name="reportfrequency"), nullable=False),
        sa.Column("due_offset_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("submission_method", sa.String(255)),
        sa.Column("form_link", sa.String(500)),
        sa.Column("description", sa.Text()),
    )

    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("grant_id", sa.Integer(), sa.ForeignKey("grants.id"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("reporting_requirements.id"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("fiscal_period_covered", sa.String(100)),
        sa.Column("status", sa.Enum("Not Started", "In Progress", "Submitted", "Accepted", "Closed", "Overdue", name="deadlinestatus"), nullable=False, server_default="Not Started"),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("submitted_date", sa.Date(), nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("submission_link", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deadline_id", sa.Integer(), sa.ForeignKey("deadlines.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("deadlines")
    op.drop_table("reporting_requirements")
    op.drop_table("grants")
    op.drop_table("staff")
    op.drop_table("funders")
    op.execute("DROP TYPE IF EXISTS deadlinestatus")
    op.execute("DROP TYPE IF EXISTS reportfrequency")
    op.execute("DROP TYPE IF EXISTS fundertype")
