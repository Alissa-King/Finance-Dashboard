import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, Date,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class FunderType(str, enum.Enum):
    federal = "federal"
    state = "state"
    local = "local"
    private_foundation = "private_foundation"
    other = "other"


class ReportFrequency(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    semi_annual = "semi_annual"
    annual = "annual"
    one_time = "one_time"


class DeadlineStatus(str, enum.Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    submitted = "Submitted"
    accepted = "Accepted"
    closed = "Closed"
    overdue = "Overdue"


class Funder(Base):
    __tablename__ = "funders"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, nullable=False, default=1)
    name = Column(String(255), nullable=False)
    type = Column(Enum(FunderType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    parent_agency = Column(String(255))
    website = Column(String(500))
    notes = Column(Text)

    grants = relationship("Grant", back_populates="funder")
    requirements = relationship("ReportingRequirement", back_populates="funder")


class Grant(Base):
    __tablename__ = "grants"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, nullable=False, default=1)
    funder_id = Column(Integer, ForeignKey("funders.id"), nullable=False)
    grant_name = Column(String(255), nullable=False)
    award_number = Column(String(100))
    program = Column(String(255))
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    award_amount = Column(Numeric(15, 2))
    program_officer_name = Column(String(255))
    program_officer_email = Column(String(255))
    notes = Column(Text)

    funder = relationship("Funder", back_populates="grants")
    deadlines = relationship("Deadline", back_populates="grant")


class ReportingRequirement(Base):
    __tablename__ = "reporting_requirements"

    id = Column(Integer, primary_key=True)
    funder_id = Column(Integer, ForeignKey("funders.id"), nullable=True)
    name = Column(String(255), nullable=False)
    frequency = Column(Enum(ReportFrequency, values_callable=lambda x: [e.value for e in x]), nullable=False)
    due_offset_days = Column(Integer, nullable=False, default=30)
    submission_method = Column(String(255))
    form_link = Column(String(500))
    description = Column(Text)

    funder = relationship("Funder", back_populates="requirements")
    deadlines = relationship("Deadline", back_populates="requirement")


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, nullable=False, default=1)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    role = Column(String(100))

    deadlines = relationship("Deadline", back_populates="assignee")
    audit_logs = relationship("AuditLog", back_populates="user")


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, nullable=False, default=1)
    grant_id = Column(Integer, ForeignKey("grants.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("reporting_requirements.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    fiscal_period_covered = Column(String(100))
    status = Column(Enum(DeadlineStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=DeadlineStatus.not_started)
    assigned_to = Column(Integer, ForeignKey("staff.id"), nullable=True)
    submitted_date = Column(Date, nullable=True)
    submitted_by = Column(String(255), nullable=True)
    submission_link = Column(String(500), nullable=True)
    notes = Column(Text)

    grant = relationship("Grant", back_populates="deadlines")
    requirement = relationship("ReportingRequirement", back_populates="deadlines")
    assignee = relationship("Staff", back_populates="deadlines")
    audit_logs = relationship("AuditLog", back_populates="deadline")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    deadline_id = Column(Integer, ForeignKey("deadlines.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text)

    deadline = relationship("Deadline", back_populates="audit_logs")
    user = relationship("Staff", back_populates="audit_logs")
