from pydantic import BaseModel, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import date


class EventMenuItemRead(BaseModel):
    id: UUID
    cocktail_recipe_id: UUID
    cocktail_name: Optional[str] = None
    cocktail_name_he: Optional[str] = None


class EventRead(BaseModel):
    id: UUID
    name: Optional[str] = None
    notes: Optional[str] = None
    event_date: date
    people: int
    servings_per_person: float
    menu_items: List[EventMenuItemRead]


class EventCreate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    event_date: date
    people: int
    servings_per_person: float = 3.0
    cocktail_names: List[str]

    @field_validator("cocktail_names")
    @classmethod
    def validate_cocktail_names(cls, v: List[str]) -> List[str]:
        names = [(x or "").strip() for x in (v or [])]
        names = [x for x in names if x]
        if len(names) != 4:
            raise ValueError("cocktail_names must contain exactly 4 non-empty names")
        return names


class EventUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    event_date: Optional[date] = None
    people: Optional[int] = None
    servings_per_person: Optional[float] = None
    cocktail_names: Optional[List[str]] = None

