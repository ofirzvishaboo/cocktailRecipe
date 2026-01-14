"""
Inventory v3 (two locations: BAR/WAREHOUSE).

Models:
- InventoryItem (backed by Bottle OR Ingredient OR GlassType)
- InventoryStock (quantity per item per location)
- InventoryMovement (append-only deltas that update stock)
"""

