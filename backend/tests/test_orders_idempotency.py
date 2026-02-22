"""Unit tests for order idempotency logic (prefer RECEIVED over DRAFT, avoid duplicates)."""

import pytest
from uuid import uuid4


def _build_existing_map_prefer_non_draft(orders: list, key_fn) -> dict:
    """Mirrors the prefer-non-DRAFT logic in routers/orders.py."""
    result = {}
    for o in orders:
        key = key_fn(o)
        if key is None:
            continue
        curr = result.get(key)
        if curr is None or (
            (o.get("status") or "").upper() != "DRAFT"
            and ((curr.get("status") or "").upper() == "DRAFT")
        ):
            result[key] = o
    return result


def test_prefer_received_over_draft_weekly():
    """When both DRAFT and RECEIVED exist for same supplier, prefer RECEIVED."""
    sid = uuid4()
    draft = {"id": uuid4(), "supplier_id": sid, "status": "DRAFT"}
    received = {"id": uuid4(), "supplier_id": sid, "status": "RECEIVED"}
    orders = [draft, received]
    key_fn = lambda o: o.get("supplier_id")
    result = _build_existing_map_prefer_non_draft(orders, key_fn)
    assert result[sid]["status"] == "RECEIVED"
    assert result[sid]["id"] == received["id"]


def test_prefer_received_over_draft_reverse_order():
    """Prefer RECEIVED even when it comes first in the list."""
    sid = uuid4()
    received = {"id": uuid4(), "supplier_id": sid, "status": "RECEIVED"}
    draft = {"id": uuid4(), "supplier_id": sid, "status": "DRAFT"}
    orders = [received, draft]
    key_fn = lambda o: o.get("supplier_id")
    result = _build_existing_map_prefer_non_draft(orders, key_fn)
    assert result[sid]["status"] == "RECEIVED"


def test_single_draft_kept():
    """When only DRAFT exists, keep it."""
    sid = uuid4()
    draft = {"id": uuid4(), "supplier_id": sid, "status": "DRAFT"}
    orders = [draft]
    key_fn = lambda o: o.get("supplier_id")
    result = _build_existing_map_prefer_non_draft(orders, key_fn)
    assert result[sid]["status"] == "DRAFT"


def test_single_received_kept():
    """When only RECEIVED exists, keep it."""
    sid = uuid4()
    received = {"id": uuid4(), "supplier_id": sid, "status": "RECEIVED"}
    orders = [received]
    key_fn = lambda o: o.get("supplier_id")
    result = _build_existing_map_prefer_non_draft(orders, key_fn)
    assert result[sid]["status"] == "RECEIVED"


def test_event_key_prefer_received():
    """Event scope: prefer non-DRAFT for (event_id, supplier_id)."""
    eid, sid = uuid4(), uuid4()
    draft = {"id": uuid4(), "event_id": eid, "supplier_id": sid, "status": "DRAFT"}
    received = {"id": uuid4(), "event_id": eid, "supplier_id": sid, "status": "RECEIVED"}
    orders = [draft, received]
    key_fn = lambda o: (o.get("event_id"), o.get("supplier_id")) if o.get("event_id") else None
    result = _build_existing_map_prefer_non_draft(orders, key_fn)
    assert result[(eid, sid)]["status"] == "RECEIVED"
