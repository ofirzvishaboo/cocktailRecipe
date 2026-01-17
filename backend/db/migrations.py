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

async def drop_legacy_tables_if_exist(engine: AsyncEngine):
    """Drop legacy tables that are no longer used."""
    async with engine.begin() as conn:
        # These were the pre-normalization tables.
        await conn.execute(text("DROP TABLE IF EXISTS cocktail_ingredients CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS ingredient_brands CASCADE"))

async def recreate_inventory_v3_tables(engine: AsyncEngine):
    """
    Inventory v3 (two fixed locations: BAR/WAREHOUSE).

    Strategy: drop + recreate inventory tables if any legacy/mismatched tables exist.
    This is intentionally a "clean break" migration.
    """
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('inventory_items', 'inventory_stock', 'inventory_movements')
                """
            )
        )
        existing = {r[0] for r in res.fetchall()}

        expected_columns = {
            "inventory_items": {
                "id",
                "item_type",
                "bottle_id",
                "ingredient_id",
                "glass_type_id",
                "name",
                "unit",
                "is_active",
                "min_level",
                "reorder_level",
                "price_minor",
                "currency",
            },
            "inventory_stock": {"id", "location", "inventory_item_id", "quantity", "reserved_quantity"},
            "inventory_movements": {
                "id",
                "location",
                "inventory_item_id",
                "change",
                "reason",
                "source_type",
                "source_id",
                "created_at",
                "created_by_user_id",
            },
        }

        expected_constraints = {
            "inventory_items": {
                "ck_inventory_items_item_type",
                "ck_inventory_items_backing_fk",
                "fk_inventory_items_bottle_id",
                "fk_inventory_items_ingredient_id",
                "fk_inventory_items_glass_type_id",
            },
            "inventory_stock": {
                "ck_inventory_stock_location",
                "fk_inventory_stock_inventory_item_id",
                "ux_inventory_stock_location_item",
            },
            "inventory_movements": {
                "ck_inventory_movements_location",
                "fk_inventory_movements_inventory_item_id",
                "fk_inventory_movements_created_by_user_id",
            },
        }

        expected_indexes = {
            "ux_inventory_items_bottle_id",
            "ux_inventory_items_ingredient_id",
            "ux_inventory_items_glass_type_id",
            "ix_inventory_items_item_type",
            "ix_inventory_items_name",
            "ix_inventory_stock_item_id",
            "ix_inventory_movements_item_id",
            "ix_inventory_movements_created_at",
        }

        async def _table_columns(table: str) -> set[str]:
            r = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name = :t
                    """
                ),
                {"t": table},
            )
            return {row[0] for row in r.fetchall()}

        async def _table_constraints(table: str) -> set[str]:
            r = await conn.execute(
                text(
                    """
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_schema='public' AND table_name = :t
                    """
                ),
                {"t": table},
            )
            return {row[0] for row in r.fetchall()}

        async def _all_indexes() -> set[str]:
            r = await conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname='public'
                      AND tablename IN ('inventory_items','inventory_stock','inventory_movements')
                    """
                )
            )
            return {row[0] for row in r.fetchall()}

        needs_recreate = False

        if existing != {"inventory_items", "inventory_stock", "inventory_movements"}:
            # Partial existence or missing tables: make it consistent.
            needs_recreate = True
        else:
            # Allow safe additive migrations (do NOT drop data).
            additive_columns = {
                "inventory_items": {
                    "price_minor": "INTEGER",
                    "currency": "TEXT",
                }
            }
            for t in ("inventory_items", "inventory_stock", "inventory_movements"):
                cols = await _table_columns(t)
                missing = expected_columns[t] - cols
                if missing and t in additive_columns and missing.issubset(set(additive_columns[t].keys())):
                    for col in sorted(missing):
                        col_type = additive_columns[t][col]
                        await conn.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS {col} {col_type} NULL"))
                    cols |= missing
                # Allow additive columns (forward-compatible). We only require the expected ones.
                if not expected_columns[t].issubset(cols):
                    needs_recreate = True
                    break
                cons = await _table_constraints(t)
                if not expected_constraints[t].issubset(cons):
                    needs_recreate = True
                    break

            if not needs_recreate:
                idxs = await _all_indexes()
                if not expected_indexes.issubset(idxs):
                    needs_recreate = True

        if needs_recreate:
            if existing:
                print(f"[migrations] Recreating inventory tables (drop+recreate). Existing: {sorted(existing)}")
            else:
                print("[migrations] Creating inventory tables (fresh).")
            # Drop in dependency order (FKs -> parent), CASCADE keeps it simple.
            await conn.execute(text("DROP TABLE IF EXISTS inventory_movements CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS inventory_stock CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS inventory_items CASCADE"))

        # Create tables (fresh or after drop), or ensure present if missing.
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS inventory_items (
                    id UUID PRIMARY KEY,
                    item_type TEXT NOT NULL,
                    bottle_id UUID NULL,
                    ingredient_id UUID NULL,
                    glass_type_id UUID NULL,
                    name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    min_level NUMERIC NULL,
                    reorder_level NUMERIC NULL,
                    price_minor INTEGER NULL,
                    currency TEXT NULL,
                    CONSTRAINT ck_inventory_items_item_type
                        CHECK (item_type IN ('BOTTLE','GARNISH','GLASS')),
                    CONSTRAINT ck_inventory_items_backing_fk
                        CHECK (
                            (item_type = 'BOTTLE' AND bottle_id IS NOT NULL AND ingredient_id IS NULL AND glass_type_id IS NULL)
                            OR
                            (item_type = 'GARNISH' AND ingredient_id IS NOT NULL AND bottle_id IS NULL AND glass_type_id IS NULL)
                            OR
                            (item_type = 'GLASS' AND glass_type_id IS NOT NULL AND bottle_id IS NULL AND ingredient_id IS NULL)
                        ),
                    CONSTRAINT fk_inventory_items_bottle_id
                        FOREIGN KEY (bottle_id) REFERENCES bottles(id) ON DELETE CASCADE,
                    CONSTRAINT fk_inventory_items_ingredient_id
                        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
                    CONSTRAINT fk_inventory_items_glass_type_id
                        FOREIGN KEY (glass_type_id) REFERENCES glass_types(id) ON DELETE CASCADE
                )
                """
            )
        )

        # Additive migration: add new columns if table already existed.
        await conn.execute(text("ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS price_minor INTEGER NULL"))
        await conn.execute(text("ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS currency TEXT NULL"))

        # Ensure at-most-one inventory item per backing entity (partial unique indexes).
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_inventory_items_bottle_id
                    ON inventory_items(bottle_id)
                    WHERE bottle_id IS NOT NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_inventory_items_ingredient_id
                    ON inventory_items(ingredient_id)
                    WHERE ingredient_id IS NOT NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_inventory_items_glass_type_id
                    ON inventory_items(glass_type_id)
                    WHERE glass_type_id IS NOT NULL
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_items_item_type ON inventory_items(item_type)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_items_name ON inventory_items(name)"))

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS inventory_stock (
                    id UUID PRIMARY KEY,
                    location TEXT NOT NULL,
                    inventory_item_id UUID NOT NULL,
                    quantity NUMERIC NOT NULL DEFAULT 0,
                    reserved_quantity NUMERIC NOT NULL DEFAULT 0,
                    CONSTRAINT ck_inventory_stock_location
                        CHECK (location IN ('BAR','WAREHOUSE')),
                    CONSTRAINT fk_inventory_stock_inventory_item_id
                        FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
                    CONSTRAINT ux_inventory_stock_location_item
                        UNIQUE (location, inventory_item_id)
                )
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_stock_item_id ON inventory_stock(inventory_item_id)"))

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id UUID PRIMARY KEY,
                    location TEXT NOT NULL,
                    inventory_item_id UUID NOT NULL,
                    change NUMERIC NOT NULL,
                    reason TEXT NULL,
                    source_type TEXT NULL,
                    source_id BIGINT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    created_by_user_id UUID NULL,
                    CONSTRAINT ck_inventory_movements_location
                        CHECK (location IN ('BAR','WAREHOUSE')),
                    CONSTRAINT fk_inventory_movements_inventory_item_id
                        FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
                    CONSTRAINT fk_inventory_movements_created_by_user_id
                        FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                )
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_movements_item_id ON inventory_movements(inventory_item_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_inventory_movements_created_at ON inventory_movements(created_at)"))


async def ensure_ingredient_taxonomy(engine: AsyncEngine):
    """
    Ensure Kind='Ingredient' and its Subcategories exist:
    Spirit, Liqueur, Juice, Syrup, Garnish.
    """
    subcats = ["Spirit", "Liqueur", "Juice", "Syrup", "Garnish"]
    async with engine.begin() as conn:
        # Kind
        res = await conn.execute(
            text("SELECT id FROM kinds WHERE lower(name) = lower(:name) LIMIT 1"),
            {"name": "Ingredient"},
        )
        kind_id = res.scalar_one_or_none()
        if not kind_id:
            kind_id = str(uuid.uuid4())
            await conn.execute(
                text("INSERT INTO kinds (id, name) VALUES (:id, :name)"),
                {"id": kind_id, "name": "Ingredient"},
            )

        # Subcategories (idempotent)
        for name in subcats:
            r = await conn.execute(
                text(
                    """
                    SELECT id FROM subcategories
                    WHERE kind_id = :kind_id AND lower(name) = lower(:name)
                    LIMIT 1
                    """
                ),
                {"kind_id": kind_id, "name": name},
            )
            existing = r.scalar_one_or_none()
            if existing:
                continue
            await conn.execute(
                text("INSERT INTO subcategories (id, kind_id, name) VALUES (:id, :kind_id, :name)"),
                {"id": str(uuid.uuid4()), "kind_id": kind_id, "name": name},
            )


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
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS preparation_method TEXT"))
        await conn.execute(text("ALTER TABLE cocktail_recipes ADD COLUMN IF NOT EXISTS batch_type TEXT"))

        # populate defaults for existing rows
        await conn.execute(text("UPDATE cocktail_recipes SET updated_at = COALESCE(updated_at, created_at, NOW())"))
        # legacy: if an older column exists, you can migrate it manually before dropping it

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


## Legacy backfill removed by design (clean break).

