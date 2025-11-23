from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.database import create_db_and_tables
from routers.cocktails import router as cocktails_router
from routers.ingredients import router as ingredients_router
from routers.cocktail_ingredient import router as cocktail_ingredient_router
from routers.images import router as images_router
from contextlib import asynccontextmanager


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


# Image upload routes
app.include_router(images_router, prefix="/images", tags=["images"])

# Cocktail recipe routes
app.include_router(cocktail_ingredient_router, prefix="/cocktail-ingredients", tags=["cocktail-ingredients"])
app.include_router(cocktails_router, prefix="/cocktail-recipes", tags=["cocktails"])
app.include_router(ingredients_router, prefix="/ingredients", tags=["ingredients"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)