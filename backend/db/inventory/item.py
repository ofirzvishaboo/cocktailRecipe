import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 'BOTTLE' | 'GARNISH' | 'GLASS'
    item_type = Column(Text, nullable=False, index=True)

    bottle_id = Column(UUID(as_uuid=True), ForeignKey("bottles.id", ondelete="CASCADE"), nullable=True, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=True, index=True)
    glass_type_id = Column(UUID(as_uuid=True), ForeignKey("glass_types.id", ondelete="CASCADE"), nullable=True, index=True)

    name = Column(String, nullable=False)
    unit = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    min_level = Column(Numeric, nullable=True)
    reorder_level = Column(Numeric, nullable=True)

    bottle = relationship("Bottle")
    ingredient = relationship("Ingredient")
    glass_type = relationship("GlassType")

    stocks = relationship("InventoryStock", back_populates="inventory_item", cascade="all, delete-orphan")
    movements = relationship("InventoryMovement", back_populates="inventory_item", cascade="all, delete-orphan")

