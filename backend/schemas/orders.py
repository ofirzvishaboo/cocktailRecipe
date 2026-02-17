from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import date


class OrderItemRead(BaseModel):
    id: Optional[UUID] = None
    ingredient_id: UUID
    ingredient_name: Optional[str] = None
    ingredient_name_he: Optional[str] = None
    requested_ml: Optional[float] = None
    requested_quantity: Optional[float] = None
    requested_unit: Optional[str] = None
    used_from_stock_ml: Optional[float] = None
    used_from_stock_quantity: Optional[float] = None
    needed_ml: Optional[float] = None
    needed_quantity: Optional[float] = None
    unit: Optional[str] = None
    bottle_id: Optional[UUID] = None
    bottle_name: Optional[str] = None
    bottle_name_he: Optional[str] = None
    bottle_volume_ml: Optional[int] = None
    recommended_bottles: Optional[int] = None
    leftover_ml: Optional[float] = None


class OrderRead(BaseModel):
    id: UUID
    scope: str
    event_id: Optional[UUID] = None
    event_date: Optional[date] = None
    event_name: Optional[str] = None
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    status: str
    period_start: date
    period_end: date
    notes: Optional[str] = None
    items: List[OrderItemRead]


class OrderItemUpdate(BaseModel):
    needed_ml: Optional[float] = None
    needed_quantity: Optional[float] = None
    unit: Optional[str] = None
    bottle_id: Optional[UUID] = None
    bottle_volume_ml: Optional[int] = None
    recommended_bottles: Optional[int] = None
    leftover_ml: Optional[float] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class AddToStockRequest(BaseModel):
    location: str = "WAREHOUSE"  # BAR | WAREHOUSE


class WeeklyOrderRequest(BaseModel):
    order_date: Optional[date] = None
    location_scope: str = "ALL"  # ALL|BAR|WAREHOUSE


class WeeklyOrderResponse(BaseModel):
    period_start: date
    period_end: date
    created_order_ids: List[UUID]
    updated_order_ids: List[UUID] = []
    skipped_order_ids: List[UUID] = []
    missing_suppliers_ingredient_ids: List[UUID]
    missing_suppliers_ingredient_names: List[str]


class WeeklyByEventSupplierGroup(BaseModel):
    supplier_id: Optional[UUID] = None
    supplier_name: Optional[str] = None
    order_id: Optional[UUID] = None
    items: List[OrderItemRead]


class WeeklyByEventEventGroup(BaseModel):
    event_id: UUID
    event_date: date
    event_name: Optional[str] = None
    suppliers: List[WeeklyByEventSupplierGroup]


class WeeklyByEventResponse(BaseModel):
    period_start: date
    period_end: date
    events: List[WeeklyByEventEventGroup]
    weekly_summary: List[WeeklyByEventSupplierGroup]
    created_event_order_ids: List[UUID] = []
    updated_event_order_ids: List[UUID] = []
    skipped_event_order_ids: List[UUID] = []
    created_weekly_order_ids: List[UUID] = []
    updated_weekly_order_ids: List[UUID] = []
    skipped_weekly_order_ids: List[UUID] = []
    missing_suppliers_ingredient_ids: List[UUID] = []
    missing_suppliers_ingredient_names: List[str] = []

