import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False, unique=True)  # opening | closing
    name = Column(String, nullable=False)

    sections = relationship("ChecklistSection", back_populates="template", cascade="all, delete-orphan")
    runs = relationship("ChecklistRun", back_populates="template")


class ChecklistSection(Base):
    __tablename__ = "checklist_sections"
    __table_args__ = (
        UniqueConstraint("template_id", "key", name="uq_checklist_section_template_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False)
    title_he = Column(String, nullable=False)
    title_en = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    section_type = Column(String, nullable=False, default="checkbox")  # checkbox | daily_rotation | text_fields

    template = relationship("ChecklistTemplate", back_populates="sections")
    items = relationship("ChecklistItem", back_populates="section", cascade="all, delete-orphan", order_by="ChecklistItem.sort_order")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    __table_args__ = (
        UniqueConstraint("section_id", "key", name="uq_checklist_item_section_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(UUID(as_uuid=True), ForeignKey("checklist_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False)
    text_he = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    day_of_week = Column(Integer, nullable=True)  # 0=Sun .. 6=Sat for daily_rotation

    section = relationship("ChecklistSection", back_populates="items")


class ChecklistRun(Base):
    __tablename__ = "checklist_runs"
    __table_args__ = (
        UniqueConstraint("run_date", "template_id", name="uq_checklist_run_date_template"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    run_date = Column(Date, nullable=False, index=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress | submitted
    submitted_by_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    template = relationship("ChecklistTemplate", back_populates="runs")
    submitted_by = relationship("Staff", foreign_keys=[submitted_by_staff_id])
    submitted_by_user = relationship("User", foreign_keys=[submitted_by_user_id])
    completions = relationship("ChecklistRunCompletion", back_populates="run", cascade="all, delete-orphan")
    notes = relationship("ChecklistRunNote", back_populates="run", cascade="all, delete-orphan")


class ChecklistRunCompletion(Base):
    __tablename__ = "checklist_run_completions"
    __table_args__ = (
        UniqueConstraint("run_id", "item_id", name="uq_checklist_run_completion_run_item"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("checklist_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False, index=True)
    completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    run = relationship("ChecklistRun", back_populates="completions")
    item = relationship("ChecklistItem")


class ChecklistRunNote(Base):
    __tablename__ = "checklist_run_notes"
    __table_args__ = (
        UniqueConstraint("run_id", "field_key", name="uq_checklist_run_note_run_field"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("checklist_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    field_key = Column(String, nullable=False)
    value = Column(Text, nullable=False, default="")

    run = relationship("ChecklistRun", back_populates="notes")
