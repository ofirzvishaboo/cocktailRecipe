"""Database migration utilities"""
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker


async def add_missing_user_columns(engine: AsyncEngine):
    """Add missing columns to users table required by fastapi-users"""
    async with engine.begin() as conn:
        # Check which columns exist
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
            """)
        )
        existing_columns = {row[0] for row in result.fetchall()}

        # fastapi-users requires: id, email, hashed_password, is_active, is_superuser, is_verified
        required_columns = {
            'is_superuser': ('BOOLEAN', 'FALSE'),
            'is_verified': ('BOOLEAN', 'FALSE'),
            'is_active': ('BOOLEAN', 'TRUE'),
        }

        for column_name, (column_type, default_value) in required_columns.items():
            if column_name not in existing_columns:
                print(f"Adding {column_name} column to users table...")
                # First add as nullable with default
                await conn.execute(
                    text(f"""
                        ALTER TABLE users
                        ADD COLUMN {column_name} {column_type} DEFAULT {default_value}
                    """)
                )
                # Update any existing NULL values (shouldn't be any, but just in case)
                await conn.execute(
                    text(f"""
                        UPDATE users
                        SET {column_name} = {default_value}
                        WHERE {column_name} IS NULL
                    """)
                )
                # Now make it NOT NULL
                await conn.execute(
                    text(f"""
                        ALTER TABLE users
                        ALTER COLUMN {column_name} SET NOT NULL
                    """)
                )
                print(f"Successfully added {column_name} column to users table")
            else:
                print(f"{column_name} column already exists in users table")

        # Handle the 'role' column if it exists - make it nullable or add default
        if 'role' in existing_columns:
            print("Found 'role' column in users table. Making it nullable to avoid conflicts...")
            try:
                # Check if it's currently NOT NULL
                constraint_result = await conn.execute(
                    text("""
                        SELECT is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name = 'role'
                    """)
                )
                role_info = constraint_result.fetchone()

                if role_info and role_info[0] == 'NO':
                    # If it's NOT NULL and has no default, we need to either:
                    # 1. Set a default value for existing rows and add a default
                    # 2. Make it nullable
                    # Let's make it nullable since it's not part of the User model
                    await conn.execute(
                        text("""
                            ALTER TABLE users
                            ALTER COLUMN role DROP NOT NULL
                        """)
                    )
                    print("Successfully made 'role' column nullable")
                else:
                    print("'role' column is already nullable or has a default")
            except Exception as e:
                print(f"Warning: Could not modify 'role' column: {e}")


async def add_user_id_column_if_missing(engine: AsyncEngine):
    """Add user_id column to cocktail_recipes table if it doesn't exist"""
    # Check if the column exists by querying the information_schema
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cocktail_recipes'
                AND column_name = 'user_id'
            """)
        )
        column_exists = result.scalar() is not None

        if not column_exists:
            print("Adding user_id column to cocktail_recipes table...")

            # First, add the column as nullable
            await conn.execute(
                text("""
                    ALTER TABLE cocktail_recipes
                    ADD COLUMN user_id UUID
                """)
            )

            # Delete any existing rows that don't have a user_id
            # (since we can't assign them to a user)
            await conn.execute(
                text("""
                    DELETE FROM cocktail_recipes
                    WHERE user_id IS NULL
                """)
            )

            # Check if foreign key constraint already exists
            fk_result = await conn.execute(
                text("""
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = 'cocktail_recipes'
                    AND constraint_name = 'fk_cocktail_recipes_user_id'
                """)
            )
            fk_exists = fk_result.scalar() is not None

            if not fk_exists:
                # Now add the foreign key constraint
                await conn.execute(
                    text("""
                        ALTER TABLE cocktail_recipes
                        ADD CONSTRAINT fk_cocktail_recipes_user_id
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE
                    """)
                )

            # Make the column non-nullable
            await conn.execute(
                text("""
                    ALTER TABLE cocktail_recipes
                    ALTER COLUMN user_id SET NOT NULL
                """)
            )

            print("Successfully added user_id column to cocktail_recipes table")
        else:
            print("user_id column already exists in cocktail_recipes table")

        # Add description column if it doesn't exist
        desc_result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cocktail_recipes'
                AND column_name = 'description'
            """)
        )
        desc_exists = desc_result.scalar() is not None

        if not desc_exists:
            print("Adding description column to cocktail_recipes table...")
            await conn.execute(
                text("""
                    ALTER TABLE cocktail_recipes
                    ADD COLUMN description TEXT
                """)
            )
            print("Successfully added description column to cocktail_recipes table")
        else:
            print("description column already exists in cocktail_recipes table")


async def add_ingredient_brands_table_if_missing(engine: AsyncEngine):
    """Create ingredient_brands table if it doesn't exist"""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'ingredient_brands'
            """)
        )
        table_exists = result.scalar() is not None

        if table_exists:
            print("ingredient_brands table already exists")
            return

        print("Creating ingredient_brands table...")
        await conn.execute(
            text("""
                CREATE TABLE ingredient_brands (
                    id UUID PRIMARY KEY,
                    ingredient_id UUID NOT NULL,
                    brand_name VARCHAR NOT NULL,
                    bottle_size_ml INTEGER NOT NULL,
                    bottle_price NUMERIC NOT NULL,
                    CONSTRAINT fk_ingredient_brands_ingredient_id
                        FOREIGN KEY (ingredient_id)
                        REFERENCES ingredients(id)
                        ON DELETE CASCADE
                )
            """)
        )
        await conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_ingredient_brands_ingredient_id
                ON ingredient_brands(ingredient_id)
            """)
        )
        print("Successfully created ingredient_brands table")


async def add_ingredient_brand_id_to_cocktail_ingredients_if_missing(engine: AsyncEngine):
    """Add ingredient_brand_id column to cocktail_ingredients table if it doesn't exist"""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cocktail_ingredients'
                AND column_name = 'ingredient_brand_id'
            """)
        )
        column_exists = result.scalar() is not None

        if not column_exists:
            print("Adding ingredient_brand_id column to cocktail_ingredients table...")
            await conn.execute(
                text("""
                    ALTER TABLE cocktail_ingredients
                    ADD COLUMN ingredient_brand_id UUID
                """)
            )
        else:
            print("ingredient_brand_id column already exists in cocktail_ingredients table")

        # Ensure FK exists
        fk_result = await conn.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'cocktail_ingredients'
                AND constraint_name = 'fk_cocktail_ingredients_ingredient_brand_id'
            """)
        )
        fk_exists = fk_result.scalar() is not None

        if not fk_exists:
            print("Adding foreign key constraint for ingredient_brand_id...")
            await conn.execute(
                text("""
                    ALTER TABLE cocktail_ingredients
                    ADD CONSTRAINT fk_cocktail_ingredients_ingredient_brand_id
                    FOREIGN KEY (ingredient_brand_id)
                    REFERENCES ingredient_brands(id)
                    ON DELETE SET NULL
                """)
            )
            print("Successfully added foreign key constraint for ingredient_brand_id")
        else:
            print("Foreign key constraint for ingredient_brand_id already exists")


async def add_normalized_schema_tables_if_missing(engine: AsyncEngine):
    """Create new normalized tables if they don't exist (create_all handles most, but keep for safety)."""
    async with engine.begin() as conn:
        # These should exist via Base.metadata.create_all, but this keeps startup resilient.
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS brands (
                    id UUID PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_brands_name ON brands(name)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS kinds (
                    id UUID PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_kinds_name ON kinds(name)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS subcategories (
                    id UUID PRIMARY KEY,
                    kind_id UUID NOT NULL,
                    name VARCHAR NOT NULL,
                    CONSTRAINT fk_subcategories_kind_id
                        FOREIGN KEY (kind_id) REFERENCES kinds(id) ON DELETE CASCADE
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_subcategories_kind_id ON subcategories(kind_id)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS importers (
                    id UUID PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_importers_name ON importers(name)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS glass_types (
                    id UUID PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    capacity_ml INTEGER
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_glass_types_name ON glass_types(name)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS bottles (
                    id UUID PRIMARY KEY,
                    ingredient_id UUID NOT NULL,
                    name VARCHAR NOT NULL,
                    volume_ml INTEGER NOT NULL,
                    importer_id UUID,
                    description TEXT,
                    is_default_cost BOOLEAN NOT NULL DEFAULT FALSE,
                    CONSTRAINT fk_bottles_ingredient_id
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
                    CONSTRAINT fk_bottles_importer_id
                        FOREIGN KEY (importer_id) REFERENCES importers(id) ON DELETE SET NULL
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bottles_ingredient_id ON bottles(ingredient_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bottles_is_default_cost ON bottles(is_default_cost)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS bottle_prices (
                    id UUID PRIMARY KEY,
                    bottle_id UUID NOT NULL,
                    price_minor INTEGER NOT NULL,
                    currency VARCHAR(3) NOT NULL DEFAULT 'ILS',
                    start_date DATE NOT NULL,
                    end_date DATE,
                    source TEXT,
                    CONSTRAINT fk_bottle_prices_bottle_id
                        FOREIGN KEY (bottle_id) REFERENCES bottles(id) ON DELETE CASCADE
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bottle_prices_bottle_id ON bottle_prices(bottle_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bottle_prices_dates ON bottle_prices(start_date, end_date)"))

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS recipe_ingredients (
                    id UUID PRIMARY KEY,
                    recipe_id UUID NOT NULL,
                    ingredient_id UUID NOT NULL,
                    quantity NUMERIC(10,3) NOT NULL,
                    unit TEXT NOT NULL,
                    bottle_id UUID,
                    is_garnish BOOLEAN NOT NULL DEFAULT FALSE,
                    is_optional BOOLEAN NOT NULL DEFAULT FALSE,
                    sort_order INTEGER,
                    CONSTRAINT fk_recipe_ingredients_recipe_id
                        FOREIGN KEY (recipe_id) REFERENCES cocktail_recipes(id) ON DELETE CASCADE,
                    CONSTRAINT fk_recipe_ingredients_ingredient_id
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT,
                    CONSTRAINT fk_recipe_ingredients_bottle_id
                        FOREIGN KEY (bottle_id) REFERENCES bottles(id) ON DELETE SET NULL
                )
            """)
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_ingredient_id ON recipe_ingredients(ingredient_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_bottle_id ON recipe_ingredients(bottle_id)"))


async def add_normalized_columns_if_missing(engine: AsyncEngine):
    """Add new nullable columns to existing tables (ingredients, cocktail_recipes) if missing."""
    async with engine.begin() as conn:
        # ingredients columns
        await conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS brand_id UUID"))
        await conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS kind_id UUID"))
        await conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS subcategory_id UUID"))
        await conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS abv_percent NUMERIC(5,2)"))
        await conn.execute(text("ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS notes TEXT"))

        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ingredients_brand_id ON ingredients(brand_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ingredients_kind_id ON ingredients(kind_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ingredients_subcategory_id ON ingredients(subcategory_id)"))

        # FKs for ingredients (safe to add if missing; use fixed constraint names)
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name='ingredients' AND constraint_name='fk_ingredients_brand_id'
                    ) THEN
                        ALTER TABLE ingredients
                        ADD CONSTRAINT fk_ingredients_brand_id
                        FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE SET NULL;
                    END IF;
                END$$;
            """)
        )
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name='ingredients' AND constraint_name='fk_ingredients_kind_id'
                    ) THEN
                        ALTER TABLE ingredients
                        ADD CONSTRAINT fk_ingredients_kind_id
                        FOREIGN KEY (kind_id) REFERENCES kinds(id) ON DELETE SET NULL;
                    END IF;
                END$$;
            """)
        )
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name='ingredients' AND constraint_name='fk_ingredients_subcategory_id'
                    ) THEN
                        ALTER TABLE ingredients
                        ADD CONSTRAINT fk_ingredients_subcategory_id
                        FOREIGN KEY (subcategory_id) REFERENCES subcategories(id) ON DELETE SET NULL;
                    END IF;
                END$$;
            """)
        )

        # cocktail_recipes columns (keep existing 'user_id' column as created_by_user_id)
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS glass_type_id UUID"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS picture_url TEXT"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS garnish_text TEXT"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS base_recipe_id UUID"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS is_base BOOLEAN DEFAULT FALSE"))

        # populate defaults for existing rows
        await conn.execute(text("UPDATE cocktail_recipes SET updated_at = COALESCE(updated_at, created_at, NOW())"))
        await conn.execute(text("UPDATE cocktail_recipes SET picture_url = COALESCE(picture_url, image_url)"))

        # Add FKs if missing
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name='cocktail_recipes' AND constraint_name='fk_cocktail_recipes_glass_type_id'
                    ) THEN
                        ALTER TABLE cocktail_recipes
                        ADD CONSTRAINT fk_cocktail_recipes_glass_type_id
                        FOREIGN KEY (glass_type_id) REFERENCES glass_types(id) ON DELETE SET NULL;
                    END IF;
                END$$;
            """)
        )
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name='cocktail_recipes' AND constraint_name='fk_cocktail_recipes_base_recipe_id'
                    ) THEN
                        ALTER TABLE cocktail_recipes
                        ADD CONSTRAINT fk_cocktail_recipes_base_recipe_id
                        FOREIGN KEY (base_recipe_id) REFERENCES cocktail_recipes(id) ON DELETE SET NULL;
                    END IF;
                END$$;
            """)
        )


async def backfill_normalized_costing_if_needed(engine: AsyncEngine):
    """
    Backfill brands/bottles/bottle_prices/recipe_ingredients from the legacy tables:
    - ingredient_brands -> brands + bottles + bottle_prices
    - cocktail_ingredients -> recipe_ingredients
    """
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        # Quick check: if we already have recipe_ingredients, assume migrated
        ri_count = (await session.execute(text("SELECT COUNT(*) FROM recipe_ingredients"))).scalar() or 0
        legacy_count = (await session.execute(text("SELECT COUNT(*) FROM cocktail_ingredients"))).scalar() or 0

        # Backfill brands/bottles/prices if missing
        bottle_count = (await session.execute(text("SELECT COUNT(*) FROM bottles"))).scalar() or 0
        legacy_brand_count = (await session.execute(text("SELECT COUNT(*) FROM ingredient_brands"))).scalar() or 0

        if legacy_brand_count and (bottle_count == 0):
            # Insert brands from legacy ingredient_brands.brand_name
            legacy_brands = await session.execute(
                text("SELECT DISTINCT brand_name FROM ingredient_brands WHERE brand_name IS NOT NULL")
            )
            for (brand_name,) in legacy_brands.fetchall():
                await session.execute(
                    text("INSERT INTO brands (id, name) VALUES (:id, :name) ON CONFLICT (name) DO NOTHING"),
                    {"id": str(uuid.uuid4()), "name": brand_name},
                )

            # Map ingredients.brand_id when there is exactly one distinct brand_name for that ingredient
            await session.execute(
                text("""
                    WITH per_ing AS (
                        SELECT ingredient_id, MIN(brand_name) AS brand_name, COUNT(DISTINCT brand_name) AS c
                        FROM ingredient_brands
                        GROUP BY ingredient_id
                    )
                    UPDATE ingredients i
                    SET brand_id = b.id
                    FROM per_ing p
                    JOIN brands b ON b.name = p.brand_name
                    WHERE i.id = p.ingredient_id AND p.c = 1 AND i.brand_id IS NULL
                """)
            )

            # Insert bottles using ingredient_brands.id as bottles.id (preserve IDs)
            await session.execute(
                text("""
                    INSERT INTO bottles (id, ingredient_id, name, volume_ml, importer_id, description, is_default_cost)
                    SELECT
                        ib.id,
                        ib.ingredient_id,
                        (ib.brand_name || ' ' || i.name || ' ' || ib.bottle_size_ml::text || 'ml') AS name,
                        ib.bottle_size_ml,
                        NULL,
                        NULL,
                        CASE
                            WHEN EXISTS (
                                SELECT 1 FROM cocktail_ingredients ci
                                WHERE ci.ingredient_brand_id = ib.id
                            ) THEN TRUE
                            ELSE FALSE
                        END AS is_default_cost
                    FROM ingredient_brands ib
                    JOIN ingredients i ON i.id = ib.ingredient_id
                    ON CONFLICT (id) DO NOTHING
                """)
            )

            # Insert bottle_prices using bottles.id as bottle_prices.id (1 current price per bottle)
            await session.execute(
                text("""
                    INSERT INTO bottle_prices (id, bottle_id, price_minor, currency, start_date, end_date, source)
                    SELECT
                        ib.id,
                        ib.id,
                        ROUND((ib.bottle_price * 100))::int,
                        'ILS',
                        CURRENT_DATE,
                        NULL,
                        NULL
                    FROM ingredient_brands ib
                    ON CONFLICT (id) DO NOTHING
                """)
            )

        # Backfill recipe_ingredients if needed
        if legacy_count and (ri_count == 0):
            rows = await session.execute(
                text("""
                    SELECT cocktail_id, ingredient_id, ml, ingredient_brand_id
                    FROM cocktail_ingredients
                    ORDER BY cocktail_id
                """)
            )
            sort_order_map: dict[str, int] = {}
            for cocktail_id, ingredient_id, ml, ingredient_brand_id in rows.fetchall():
                key = str(cocktail_id)
                sort_order_map[key] = sort_order_map.get(key, 0) + 1
                await session.execute(
                    text("""
                        INSERT INTO recipe_ingredients
                            (id, recipe_id, ingredient_id, quantity, unit, bottle_id, is_garnish, is_optional, sort_order)
                        VALUES
                            (:id, :recipe_id, :ingredient_id, :quantity, 'ml', :bottle_id, FALSE, FALSE, :sort_order)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "recipe_id": str(cocktail_id),
                        "ingredient_id": str(ingredient_id),
                        "quantity": float(ml),
                        "bottle_id": str(ingredient_brand_id) if ingredient_brand_id else None,
                        "sort_order": sort_order_map[key],
                    },
                )

        await session.commit()

