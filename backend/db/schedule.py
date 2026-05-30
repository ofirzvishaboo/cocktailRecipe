import uuid
from datetime import time
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # bartender | cleaner | manager
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    user = relationship("User", foreign_keys=[user_id])


class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class BarScheduleSettings(Base):
    __tablename__ = "bar_schedule_settings"

    id = Column(Integer, primary_key=True, default=1)
    week_starts_on = Column(Integer, nullable=False, default=6)  # 6 = Sunday (Python weekday: Mon=0)
    friday_last_start_hour = Column(Integer, nullable=False, default=18)
    saturday_closed = Column(Boolean, nullable=False, default=True)


class ScheduleWeek(Base):
    __tablename__ = "schedule_weeks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start_date = Column(Date, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="draft")  # draft | published
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    availability = relationship("StaffAvailability", back_populates="schedule_week", cascade="all, delete-orphan")
    submissions = relationship("StaffAvailabilitySubmission", back_populates="schedule_week", cascade="all, delete-orphan")
    assignments = relationship("ScheduleAssignment", back_populates="schedule_week", cascade="all, delete-orphan")


class StaffAvailabilitySubmission(Base):
    """One row per staff member per week — marks self-service availability as sent."""
    __tablename__ = "staff_availability_submissions"
    __table_args__ = (
        UniqueConstraint("schedule_week_id", "staff_id", name="uq_staff_availability_submission_week_staff"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_week_id = Column(UUID(as_uuid=True), ForeignKey("schedule_weeks.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    schedule_week = relationship("ScheduleWeek", back_populates="submissions")
    staff = relationship("Staff")


class StaffAvailability(Base):
    __tablename__ = "staff_availability"
    __table_args__ = (
        UniqueConstraint("schedule_week_id", "staff_id", "day_of_week", name="uq_staff_availability_week_staff_day"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_week_id = Column(UUID(as_uuid=True), ForeignKey("schedule_weeks.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Sun .. 6=Sat
    available = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    schedule_week = relationship("ScheduleWeek", back_populates="availability")
    staff = relationship("Staff")


class ScheduleAssignment(Base):
    __tablename__ = "schedule_assignments"
    __table_args__ = (
        UniqueConstraint(
            "schedule_week_id",
            "day_of_week",
            "shift_template_id",
            "staff_id",
            name="uq_schedule_assignment_slot",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_week_id = Column(UUID(as_uuid=True), ForeignKey("schedule_weeks.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    shift_template_id = Column(UUID(as_uuid=True), ForeignKey("shift_templates.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)

    schedule_week = relationship("ScheduleWeek", back_populates="assignments")
    shift_template = relationship("ShiftTemplate")
    staff = relationship("Staff")
