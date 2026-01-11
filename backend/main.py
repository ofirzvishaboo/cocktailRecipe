from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from db.database import create_db_and_tables
from routers.cocktails import router as cocktails_router
from routers.ingredients import router as ingredients_router
from routers.brands import router as brands_router
from routers.images import router as images_router
from core.auth import fastapi_users, auth_backend
from contextlib import asynccontextmanager
from schemas.users import UserRead, UserCreate, UserUpdate
import traceback

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Cocktail Recipe API",
    description="API for managing cocktail recipes",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
# Note: When allow_credentials=True, you cannot use allow_origins=["*"]
# You must specify exact origins
cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://localhost:5174",  # Alternative Vite port
]

# CORS middleware must be added before routes
# This ensures CORS headers are sent even on errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Allow LAN/dev origins (e.g. http://10.0.0.112:5173) while keeping credentials enabled.
    # This is dev-friendly; tighten for production.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# Authentication routes (fastapi-users)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"],)
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

# Image upload routes
app.include_router(images_router, prefix="/images", tags=["images"])

# Cocktail recipe routes
app.include_router(cocktails_router, prefix="/cocktail-recipes", tags=["cocktails"])
app.include_router(ingredients_router, prefix="/ingredients", tags=["ingredients"])
app.include_router(brands_router, prefix="/brands", tags=["brands"])


# Global exception handler to ensure CORS headers are sent even on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and ensure CORS headers are included"""
    print(f"Unhandled exception: {exc}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)