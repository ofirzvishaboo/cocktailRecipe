from datetime import date, datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ChecklistType = Literal["opening", "closing"]
ChecklistRunStatus = Literal["in_progress", "submitted"]
SectionType = Literal["checkbox", "daily_rotation", "text_fields"]


class ChecklistItemRead(BaseModel):
    id: UUID
    key: str
    text_he: str
    text_en: str
    sort_order: int
    day_of_week: Optional[int] = None

    model_config = {"from_attributes": True}


class ChecklistSectionRead(BaseModel):
    id: UUID
    key: str
    title_he: str
    title_en: str
    sort_order: int
    section_type: SectionType
    items: List[ChecklistItemRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ChecklistTemplateRead(BaseModel):
    id: UUID
    type: ChecklistType
    name: str
    sections: List[ChecklistSectionRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ChecklistItemCompletionRead(BaseModel):
    item_id: UUID
    completed: bool
    completed_at: Optional[datetime] = None


class ChecklistRunRead(BaseModel):
    id: UUID
    template_id: UUID
    type: ChecklistType
    run_date: date
    status: ChecklistRunStatus
    submitted_by_staff_id: Optional[UUID] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    can_edit: bool = True
    sections: List[ChecklistSectionRead] = Field(default_factory=list)
    completions: List[ChecklistItemCompletionRead] = Field(default_factory=list)
    notes: Dict[str, str] = Field(default_factory=dict)
    total_items: int = 0
    completed_items: int = 0

    model_config = {"from_attributes": True}


class ChecklistRunUpdate(BaseModel):
    completions: Optional[List[ChecklistItemCompletionRead]] = None
    notes: Optional[Dict[str, str]] = None


class ChecklistRunSummary(BaseModel):
    id: UUID
    type: ChecklistType
    run_date: date
    status: ChecklistRunStatus
    submitted_by_staff_id: Optional[UUID] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    total_items: int = 0
    completed_items: int = 0

    model_config = {"from_attributes": True}
