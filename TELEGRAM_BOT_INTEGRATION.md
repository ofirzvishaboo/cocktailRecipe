# Telegram Bot API Integration Guide

This guide explains how to integrate your Telegram bot with the Cocktail Recipe Manager API to track inventory movements based on cocktail usage.

## Authentication

The API uses JWT (JSON Web Token) authentication. Your bot needs to authenticate as a user to access protected endpoints.

### 1. Create a Service Account User

First, create a dedicated user account for your Telegram bot:
- Email: `telegram-bot@yourdomain.com` (or any email)
- Password: Use a strong, randomly generated password
- Store credentials securely in your bot's environment variables

### 2. Authentication Flow

#### Step 1: Login to Get JWT Token

```http
POST /auth/jwt/login
Content-Type: application/x-www-form-urlencoded

username=telegram-bot@yourdomain.com&password=your_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Step 2: Use Token in Requests

Include the token in the `Authorization` header for all protected endpoints:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Lifetime:** Default is 7 days (604800 seconds). Configure via `JWT_LIFETIME_SECONDS` environment variable.

## API Endpoints for Bot Integration

### 0. Consume a Cocktail Batch by Liters (recommended for Telegram bot)

This endpoint lets your bot send **cocktail + liters**, and the API will reduce inventory for **all ingredients** in one request.

```http
POST /inventory/cocktails/{cocktail_id}/consume-batch
Authorization: Bearer {token}
Content-Type: application/json

{
  "liters": 5,
  "location": "BAR",
  "include_garnish": false,
  "include_optional": false,
  "reason": "Event: Friday night service (5L batch)",
  "source_type": "telegram_event",
  "source_id": 12345
}
```

Notes:
- This endpoint **requires `is_superuser=true`** (same as `/inventory/movements`).
- Recipes are typically stored in `ml`/`oz`. Inventory bottles are tracked as **`unit=bottle`**.
- The API converts “ml used” into “bottles used” using `Bottle.volume_ml`, so stock decreases by **fractional bottles**.

### 1. Get All Cocktails (with ingredients)

```http
GET /cocktail-recipes/
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Margarita",
    "recipe_ingredients": [
      {
        "id": "uuid",
        "ingredient_id": "uuid",
        "ingredient_name": "Tequila Blanco",
        "quantity": 60.0,
        "unit": "ml",
        "subcategory_name": "Spirit",
        "bottle_id": "uuid",
        "bottle_name": "Sierra Tequila Blanco 700ml"
      },
      {
        "ingredient_name": "Lime Juice",
        "quantity": 30.0,
        "unit": "ml",
        "subcategory_name": "Juice"
      }
    ]
  }
]
```

### 2. Get Single Cocktail

```http
GET /cocktail-recipes/{cocktail_id}
Authorization: Bearer {token}
```

### 3. Get Inventory Items

To find inventory items for ingredients:

```http
GET /inventory/items?item_type=BOTTLE&location=BAR
Authorization: Bearer {token}
```

**Query Parameters:**
- `item_type`: `BOTTLE`, `GARNISH`, or `GLASS`
- `location`: `BAR` or `WAREHOUSE` (optional)
- `q`: Search query (optional)

**Response:**
```json
[
  {
    "id": "uuid",
    "item_type": "BOTTLE",
    "name": "Tequila Blanco",
    "unit": "ml",
    "ingredient_id": "uuid",
    "bottle_id": "uuid"
  }
]
```

### 4. Get Current Stock

```http
GET /inventory/stock?location=BAR
Authorization: Bearer {token}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "location": "BAR",
    "inventory_item_id": "uuid",
    "quantity": 5000.0,
    "reserved_quantity": 0.0,
    "item": {
      "name": "Tequila Blanco",
      "unit": "ml"
    }
  }
]
```

### 5. Create Inventory Movement (Reduce Stock)

**Important:** This endpoint requires `is_superuser=True`. Ensure your bot user has superuser privileges.

```http
POST /inventory/movements
Authorization: Bearer {token}
Content-Type: application/json

{
  "location": "BAR",
  "inventory_item_id": "uuid-of-inventory-item",
  "change": -60.0,
  "reason": "Cocktail served: Margarita",
  "source_type": "telegram_event",
  "source_id": 12345
}
```

**Request Body:**
- `location`: `"BAR"` or `"WAREHOUSE"`
- `inventory_item_id`: UUID of the inventory item
- `change`: **Negative value** to reduce stock (e.g., `-60.0` for 60ml used)
- `reason`: Description of why stock changed (e.g., "Cocktail served: Margarita")
- `source_type`: Optional identifier for the source system (e.g., `"telegram_event"`)
- `source_id`: Optional ID from your system (e.g., Telegram event ID)

**Response:**
```json
{
  "movement": {
    "id": "uuid",
    "location": "BAR",
    "inventory_item_id": "uuid",
    "change": -60.0,
    "reason": "Cocktail served: Margarita",
    "source_type": "telegram_event",
    "source_id": 12345,
    "created_by_user_id": "uuid"
  },
  "stock": {
    "location": "BAR",
    "inventory_item_id": "uuid",
    "quantity": 4940.0,
    "reserved_quantity": 0.0
  }
}
```

## Example: Processing a Cocktail Order

Here's a complete example of how your Telegram bot should handle a cocktail order:

### Python Example

```python
import requests
import os
from typing import Dict, List, Optional
from uuid import UUID

class CocktailAPIClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self._authenticate()

    def _authenticate(self):
        """Login and store JWT token"""
        response = requests.post(
            f"{self.base_url}/auth/jwt/login",
            data={"username": self.email, "password": self.password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_cocktail(self, cocktail_id: UUID) -> Dict:
        """Get cocktail details with ingredients"""
        response = requests.get(
            f"{self.base_url}/cocktail-recipes/{cocktail_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def get_inventory_items_by_ingredient(self, ingredient_id: UUID, location: str = "BAR") -> List[Dict]:
        """Find inventory items for an ingredient"""
        # Get all items and filter client-side
        # Note: For bottle items, we need to check the bottle's ingredient_id separately
        response = requests.get(
            f"{self.base_url}/inventory/items",
            params={"location": location},
            headers=self._headers()
        )
        response.raise_for_status()
        all_items = response.json()

        # Filter items that match this ingredient_id
        # - GARNISH items have ingredient_id directly
        # - BOTTLE items need to check via bottle relationship
        matching_items = []
        ingredient_id_str = str(ingredient_id)

        for item in all_items:
            # Direct match for garnish items
            if item.get("ingredient_id") == ingredient_id_str:
                matching_items.append(item)
            # For bottle items, check if we need to resolve bottle->ingredient
            # (This requires additional API call or cached mapping)

        # Alternative: Get bottles for ingredient and match bottle_id
        if not matching_items:
            # Try to find via bottle relationship
            bottles_response = requests.get(
                f"{self.base_url}/ingredients/{ingredient_id}/bottles",
                headers=self._headers()
            )
            if bottles_response.status_code == 200:
                bottles = bottles_response.json()
                bottle_ids = {str(b["id"]) for b in bottles}
                matching_items = [
                    item for item in all_items
                    if item.get("bottle_id") in bottle_ids
                ]

        return matching_items

    def reduce_stock(self, inventory_item_id: UUID, amount: float, location: str,
                    reason: str, source_type: Optional[str] = None,
                    source_id: Optional[int] = None) -> Dict:
        """Reduce inventory stock (negative change)"""
        payload = {
            "location": location,
            "inventory_item_id": str(inventory_item_id),
            "change": -abs(amount),  # Ensure negative
            "reason": reason,
            "source_type": source_type,
            "source_id": source_id
        }
        response = requests.post(
            f"{self.base_url}/inventory/movements",
            json=payload,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def process_cocktail_order(self, cocktail_id: UUID, location: str = "BAR",
                              event_id: Optional[int] = None) -> Dict:
        """
        Process a cocktail order: get ingredients and reduce stock

        Returns summary of movements created
        """
        # Get cocktail details
        cocktail = self.get_cocktail(cocktail_id)
        cocktail_name = cocktail["name"]

        movements = []
        errors = []

        # Process each ingredient
        for ingredient in cocktail.get("recipe_ingredients", []):
            ingredient_id = ingredient.get("ingredient_id")
            ingredient_name = ingredient.get("ingredient_name")
            quantity = ingredient.get("quantity")
            unit = ingredient.get("unit")

            if not ingredient_id:
                errors.append(f"Skipping {ingredient_name}: no ingredient_id")
                continue

            # Find inventory item for this ingredient
            inventory_items = self.get_inventory_items_by_ingredient(ingredient_id, location)

            if not inventory_items:
                errors.append(f"No inventory item found for {ingredient_name} (ingredient_id: {ingredient_id})")
                continue

            # Use first matching item
            # Note: If multiple bottles exist for same ingredient, you may want to:
            # - Choose by bottle_id from recipe_ingredient if available
            # - Or implement logic to select specific bottle (e.g., by name, by stock level)
            inventory_item = inventory_items[0]

            # Optional: Match by bottle_id if recipe specifies one
            if ingredient.get("bottle_id"):
                matching_bottle = next(
                    (item for item in inventory_items if item.get("bottle_id") == str(ingredient.get("bottle_id"))),
                    None
                )
                if matching_bottle:
                    inventory_item = matching_bottle
            inventory_item_id = inventory_item["id"]

            # Reduce stock
            try:
                movement = self.reduce_stock(
                    inventory_item_id=inventory_item_id,
                    amount=quantity,
                    location=location,
                    reason=f"Cocktail served: {cocktail_name}",
                    source_type="telegram_event",
                    source_id=event_id
                )
                movements.append({
                    "ingredient": ingredient_name,
                    "quantity": quantity,
                    "unit": unit,
                    "movement": movement
                })
            except Exception as e:
                errors.append(f"Failed to reduce stock for {ingredient_name}: {str(e)}")

        return {
            "cocktail": cocktail_name,
            "movements": movements,
            "errors": errors
        }

# Usage
if __name__ == "__main__":
    client = CocktailAPIClient(
        base_url=os.getenv("COCKTAIL_API_URL", "http://localhost:8000"),
        email=os.getenv("TELEGRAM_BOT_EMAIL"),
        password=os.getenv("TELEGRAM_BOT_PASSWORD")
    )

    # Process a Margarita order
    result = client.process_cocktail_order(
        cocktail_id=UUID("your-cocktail-id-here"),
        location="BAR",
        event_id=12345  # Telegram event/message ID
    )

    print(f"Processed {result['cocktail']}")
    print(f"Created {len(result['movements'])} movements")
    if result['errors']:
        print(f"Errors: {result['errors']}")
```

## Security Best Practices

### 1. Environment Variables

Store credentials securely:

```bash
# .env file (never commit to git)
TELEGRAM_BOT_EMAIL=telegram-bot@yourdomain.com
TELEGRAM_BOT_PASSWORD=strong_random_password_here
COCKTAIL_API_URL=https://api.yourdomain.com
```

### 2. Token Refresh

Implement token refresh logic:

```python
def _ensure_authenticated(self):
    """Refresh token if expired"""
    if not self.token:
        self._authenticate()
    # Optionally check token expiry and refresh proactively
```

### 3. Error Handling

Handle authentication errors:

```python
try:
    response = requests.get(url, headers=self._headers())
    if response.status_code == 401:
        # Token expired, re-authenticate
        self._authenticate()
        response = requests.get(url, headers=self._headers())
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    # Handle API errors
    pass
```

### 4. Rate Limiting

Implement rate limiting to avoid overwhelming the API:

```python
import time
from functools import wraps

def rate_limit(calls_per_second=10):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator
```

## Setting Up Bot User as Superuser

To allow the bot to create inventory movements, the user must be a superuser. You can set this via:

1. **Database directly:**
```sql
UPDATE users SET is_superuser = TRUE WHERE email = 'telegram-bot@yourdomain.com';
```

2. **Or create a script:**
```python
# scripts/make_bot_superuser.py
from db.database import get_async_session
from db.users import User
from sqlalchemy import select

async def make_bot_superuser(email: str):
    async for db in get_async_session():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.is_superuser = True
            await db.commit()
            print(f"Made {email} a superuser")
        else:
            print(f"User {email} not found")
```

## API Base URL

- **Development:** `http://localhost:8000`
- **Production:** Your deployed API URL (e.g., `https://api.yourdomain.com`)

## Summary

1. **Authenticate** using `/auth/jwt/login` to get a JWT token
2. **Get cocktail** details with `/cocktail-recipes/{id}` to see ingredients
3. **Find inventory items** using `/inventory/items` with ingredient_id
4. **Create movements** using `/inventory/movements` with negative `change` values
5. **Store token** and include in `Authorization: Bearer {token}` header
6. **Handle errors** and implement token refresh logic
7. **Ensure bot user** has `is_superuser=True` to create movements
