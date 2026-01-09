"""Database migration utilities"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


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

