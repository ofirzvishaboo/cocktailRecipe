from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

STAFF_ROLES = ("bartender", "cleaner", "manager")


class StaffRead(BaseModel):
    id: UUID
    display_name: str
    role: str
    user_id: Optional[UUID] = None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class StaffCreate(BaseModel):
    display_name: str
    role: str
    user_id: Optional[UUID] = None
    is_active: bool = True
    sort_order: int = 0

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        r = (v or "").strip().lower()
        if r not in STAFF_ROLES:
            raise ValueError(f"role must be one of: {', '.join(STAFF_ROLES)}")
        return r


class StaffUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        r = v.strip().lower()
        if r not in STAFF_ROLES:
            raise ValueError(f"role must be one of: {', '.join(STAFF_ROLES)}")
        return r


class ShiftTemplateRead(BaseModel):
    id: UUID
    name: str
    start_time: time
    end_time: time
    sort_order: int
    active: bool

    class Config:
        from_attributes = True


class ShiftTemplateUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class BarScheduleSettingsRead(BaseModel):
    week_starts_on: int
    friday_last_start_hour: int
    saturday_closed: bool

    class Config:
        from_attributes = True


class AvailabilityEntry(BaseModel):
    staff_id: UUID
    day_of_week: int = Field(ge=0, le=6)
    available: bool
    notes: Optional[str] = None


class AvailabilityBulkUpdate(BaseModel):
    entries: List[AvailabilityEntry]


class StaffAvailabilityRead(BaseModel):
    staff_id: UUID
    staff_name: str
    role: str
    day_of_week: int
    available: bool
    notes: Optional[str] = None


class ScheduleAssignmentRead(BaseModel):
    id: UUID
    day_of_week: int
    shift_template_id: UUID
    shift_name: str
    start_time: time
    end_time: time
    staff_id: UUID
    staff_name: str
    role: str


class ScheduleGap(BaseModel):
    day_of_week: int
    role: str
    reason: str


class ScheduleWeekSummary(BaseModel):
    id: UUID
    week_start_date: date
    status: str


class StaffSubmissionStatus(BaseModel):
    staff_id: UUID
    display_name: str
    role: str
    user_id: Optional[UUID] = None
    must_self_submit: bool
    submitted: bool
    submitted_at: Optional[datetime] = None


class ScheduleWeekRead(BaseModel):
    id: UUID
    week_start_date: date
    status: str
    availability_deadline: date
    can_staff_submit: bool
    submission_status: List[StaffSubmissionStatus] = []
    templates: List[ShiftTemplateRead]
    staff: List[StaffRead]
    availability: List[StaffAvailabilityRead]
    assignments: List[ScheduleAssignmentRead]
    gaps: List[ScheduleGap] = []


class ScheduleWeekCreate(BaseModel):
    week_start: date


class GenerateResult(BaseModel):
    assignments: List[ScheduleAssignmentRead]
    gaps: List[ScheduleGap]


class AssignmentPatch(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    shift_template_id: UUID
    staff_id: Optional[UUID] = None  # null clears assignment for this slot


class ShareTextResponse(BaseModel):
    text: str


class MyStaffProfile(BaseModel):
    staff_id: UUID
    display_name: str
    role: str


class AppUserListItem(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_superuser: bool = False


class MyAvailabilityMeta(BaseModel):
    week_start_date: date
    availability_deadline: date
    can_submit: bool
    submitted: bool
    submitted_at: Optional[datetime] = None
    default_week_start: date


class PublishedShiftEntry(BaseModel):
    day_of_week: int
    shift_name: str
    start_time: time
    end_time: time
    staff_name: str
    staff_id: UUID
    role: str


class PublishedWeekView(BaseModel):
    week_start_date: date
    status: str
    assignments: List[PublishedShiftEntry] = []
