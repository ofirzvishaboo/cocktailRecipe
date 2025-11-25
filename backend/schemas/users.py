# Pydantic schemas for user-related requests/responses
# Note: fastapi-users provides its own schemas, but you can add custom ones here if needed

from pydantic import BaseModel, EmailStr
from uuid import UUID
from fastapi_users import schemas
from typing import Optional

# Example custom schemas (if you need to extend fastapi-users functionality)
# fastapi-users already provides UserRead, UserCreate, UserUpdate schemas

class UserProfile(schemas.BaseUser[UUID]):
    """Custom user profile schema if needed"""
    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool

    class Config:
        from_attributes = True

class UserRead(schemas.BaseUser[UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass
