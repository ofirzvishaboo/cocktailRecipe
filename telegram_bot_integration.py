"""
telegram_bot_integration.py

Copy this file into your Telegram-bot repo.

What it provides:
- A tiny API client for this CocktailRecipe backend (JWT login + authenticated requests)
- Example helper functions for:
  - Inventory movements (USAGE/WASTE only negative; TRANSFER via /inventory/transfers)
  - Weekly order generation (admin-only): POST /orders/weekly
  - Event CRUD (admin-only): POST /events

Environment variables expected:
- COCKTAIL_API_URL: e.g. "https://your-domain.com/api"
- COCKTAIL_API_EMAIL: bot user's email (must exist in backend)
- COCKTAIL_API_PASSWORD: bot user's password

Optional:
- COCKTAIL_API_TOKEN: if you want to pre-seed a token (otherwise we login)

Dependencies:
- requests (pip install requests)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests


class ApiError(RuntimeError):
    pass


@dataclass
class CocktailApiClient:
    base_url: str
    email: str
    password: str
    token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self) -> str:
        """
        FastAPI-Users JWT login endpoint.
        The backend uses: POST /auth/jwt/login with form fields: username, password
        """
        url = f"{self.base_url.rstrip('/')}/auth/jwt/login"
        resp = requests.post(
            url,
            data={"username": self.email, "password": self.password},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise ApiError(f"Login failed ({resp.status_code}): {resp.text}")
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise ApiError(f"Login response missing access_token: {data}")
        self.token = token
        return token

    def _request(self, method: str, path: str, *, json: Any = None, params: Dict[str, Any] | None = None) -> Any:
        if not self.token:
            self.login()

        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        resp = requests.request(
            method,
            url,
            json=json,
            params=params,
            headers=self._headers(),
            timeout=60,
        )

        # If token expired, retry once with a fresh login.
        if resp.status_code in (401, 403):
            self.login()
            resp = requests.request(
                method,
                url,
                json=json,
                params=params,
                headers=self._headers(),
                timeout=60,
            )

        if resp.status_code >= 400:
            raise ApiError(f"{method} {path} failed ({resp.status_code}): {resp.text}")

        if resp.status_code == 204:
            return None
        return resp.json()

    # ----------------------------
    # Inventory helpers
    # ----------------------------

    def create_inventory_movement(
        self,
        *,
        location: str,  # "BAR" | "WAREHOUSE"
        inventory_item_id: str,
        change: float,  # USAGE/WASTE must be <= 0
        reason: str,  # "USAGE" | "WASTE" | "ADJUSTMENT"
        notes: Optional[str] = None,
        source_type: Optional[str] = "telegram",
        source_id: Optional[str] = None,
    ) -> Any:
        """
        Calls: POST /inventory/movements

        Notes:
        - backend rejects TRANSFER here (use create_inventory_transfer)
        - backend rejects positive change for USAGE/WASTE
        """
        payload = {
            "location": location,
            "inventory_item_id": inventory_item_id,
            "change": change,
            "reason": reason,
            "notes": notes,
            "source_type": source_type,
            "source_id": source_id,
        }
        return self._request("POST", "/inventory/movements", json=payload)

    def create_inventory_transfer(
        self,
        *,
        inventory_item_id: str,
        quantity: float,
        from_location: str,  # "BAR" | "WAREHOUSE"
        to_location: str,  # "BAR" | "WAREHOUSE"
        notes: Optional[str] = None,
        source_type: Optional[str] = "telegram",
        source_id: Optional[str] = None,
    ) -> Any:
        """
        Calls: POST /inventory/transfers
        This is the atomic transfer endpoint (deduct from source, add to destination).
        """
        payload = {
            "inventory_item_id": inventory_item_id,
            "quantity": quantity,
            "from_location": from_location,
            "to_location": to_location,
            "notes": notes,
            "source_type": source_type,
            "source_id": source_id,
        }
        return self._request("POST", "/inventory/transfers", json=payload)

    # ----------------------------
    # Orders + events helpers (admin-only)
    # ----------------------------

    def generate_weekly_orders(self, *, order_date: Optional[str] = None, location_scope: str = "ALL") -> Any:
        """
        Calls: POST /orders/weekly
        admin-only: your bot user must be a superuser (is_superuser=true).
        """
        payload: Dict[str, Any] = {"location_scope": location_scope}
        if order_date:
            payload["order_date"] = order_date  # "YYYY-MM-DD"
        return self._request("POST", "/orders/weekly", json=payload)

    def create_event(
        self,
        *,
        event_date: str,  # "YYYY-MM-DD"
        people: int,
        cocktail_names: list[str],  # exactly 4 names (EN or HE; backend matches both)
        servings_per_person: float = 3.0,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Any:
        """
        Calls: POST /events
        admin-only.
        """
        payload = {
            "name": name,
            "notes": notes,
            "event_date": event_date,
            "people": people,
            "servings_per_person": servings_per_person,
            "cocktail_names": cocktail_names,
        }
        return self._request("POST", "/events", json=payload)


def make_client_from_env() -> CocktailApiClient:
    base_url = os.getenv("COCKTAIL_API_URL", "").strip()
    email = os.getenv("COCKTAIL_API_EMAIL", "").strip()
    password = os.getenv("COCKTAIL_API_PASSWORD", "").strip()
    token = os.getenv("COCKTAIL_API_TOKEN", "").strip() or None

    if not base_url:
        raise RuntimeError("Missing COCKTAIL_API_URL")
    if not email:
        raise RuntimeError("Missing COCKTAIL_API_EMAIL")
    if not password:
        raise RuntimeError("Missing COCKTAIL_API_PASSWORD")

    return CocktailApiClient(base_url=base_url, email=email, password=password, token=token)


# -----------------------------------------------------------------------------
# Minimal “manual test” usage (no Telegram libs required)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    client = make_client_from_env()

    # Example: record a usage movement (negative change)
    # client.create_inventory_movement(
    #     location="BAR",
    #     inventory_item_id="00000000-0000-0000-0000-000000000000",
    #     change=-1.0,
    #     reason="USAGE",
    #     notes="Telegram: used 1 unit",
    #     source_id=str(int(datetime.now(tz=timezone.utc).timestamp())),
    # )

    # Example: generate weekly orders (admin-only)
    # print(client.generate_weekly_orders(location_scope="ALL"))

    print("OK: client configured. Uncomment examples to run.")

