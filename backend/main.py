from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.database import create_db_and_tables
from routers.cocktails import router as cocktails_router
from routers.ingredients import router as ingredients_router
from routers.cocktail_ingredient import router as cocktail_ingredient_router
from routers.images import router as images_router
from core.auth import fastapi_users, auth_backend
from contextlib import asynccontextmanager
from schemas.users import UserRead, UserCreate, UserUpdate

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(cocktail_ingredient_router, prefix="/cocktail-ingredients", tags=["cocktail-ingredients"])
app.include_router(cocktails_router, prefix="/cocktail-recipes", tags=["cocktails"])
app.include_router(ingredients_router, prefix="/ingredients", tags=["ingredients"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)