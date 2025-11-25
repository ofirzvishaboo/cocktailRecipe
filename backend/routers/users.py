from fastapi import APIRouter
from core.auth import fastapi_users, auth_backend

router = APIRouter()

# Note: These routers should be included in main.py, not here
# This file can be used for custom user-related endpoints if needed