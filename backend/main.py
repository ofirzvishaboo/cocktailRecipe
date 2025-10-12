from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from schemas import CocktailRecipe, Ingredient
from typing import List, Dict

app = FastAPI(
    title="API",
    description="API for the project",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cocktail_memory: Dict[int, CocktailRecipe] = {
    1: CocktailRecipe(name="Marguerita", ingredients=[
        Ingredient(name='tequila', ml=50),
        Ingredient(name='lime', ml=30),
        Ingredient(name='triple sec', ml=30)
    ]),
    2: CocktailRecipe(name="Old Fashioned", ingredients=[
        Ingredient(name='whiskey', ml=60),
        Ingredient(name='sugar', ml=5),
        Ingredient(name='bitters', ml=2)
    ]),
    3: CocktailRecipe(name='Mojito', ingredients=[
        Ingredient(name='rum', ml=50),
        Ingredient(name='lime', ml=30),
        Ingredient(name='mint', ml=10),
        Ingredient(name='soda', ml=100)
    ])
}


@app.get("/cocktail-recipes", response_model=List[CocktailRecipe])
def get_cocktail_recipes():
    return list(cocktail_memory.values())


@app.get("/cocktail-recipes/{cocktail_id}", response_model=CocktailRecipe)
def get_cocktail_recipe(cocktail_id: int):
    return cocktail_memory[cocktail_id]


@app.post("/cocktail-recipes/{cocktail_id}", response_model=CocktailRecipe)
def post_cocktail_recipe(cocktail: CocktailRecipe, cocktail_id: int):
    cocktail_memory[cocktail_id] = cocktail
    return cocktail


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)