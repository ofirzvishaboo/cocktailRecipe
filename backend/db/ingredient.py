import uuid
from sqlalchemy import Column, ForeignKey, Numeric, String, Text, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Ingredient(Base):
    """Ingredient model - reusable ingredients with unique id and name.
    Suppliers are associated with Bottles, not ingredients (bottles are what suppliers supply)."""
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # Unique ingredient names
    name_he = Column(String, nullable=True)

    # Normalized fields (nullable for backfill)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True)
    kind_id = Column(UUID(as_uuid=True), ForeignKey("kinds.id", ondelete="SET NULL"), nullable=True, index=True)
    subcategory_id = Column(UUID(as_uuid=True), ForeignKey("subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    abv_percent = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)

    brand = relationship("Brand", back_populates="ingredients")
    kind = relationship("Kind", back_populates="ingredients")
    subcategory = relationship("Subcategory", back_populates="ingredients")

    bottles = relationship(
        "Bottle",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    # Property to convert model to schema dictionary format
    @property
    def to_schema(self):
        """Convert Ingredient model to schema dictionary format"""
        state = inspect(self)
        supplier_ids = None
        if "bottles" not in getattr(state, "unloaded", set()):
            supplier_ids = list({b.supplier_id for b in (self.bottles or []) if b.supplier_id is not None}) or None
        return {
            "id": self.id,
            "name": self.name,
            "name_he": self.name_he,
            "brand_id": self.brand_id,
            "kind_id": self.kind_id,
            "subcategory_id": self.subcategory_id,
            "abv_percent": float(self.abv_percent) if self.abv_percent is not None else None,
            "notes": self.notes,
            "supplier_ids": supplier_ids if supplier_ids else None,
        }

