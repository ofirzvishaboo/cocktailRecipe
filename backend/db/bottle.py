import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Bottle(Base):
    __tablename__ = "bottles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String, nullable=False)
    name_he = Column(String, nullable=True)
    volume_ml = Column(Integer, nullable=False)
    importer_id = Column(UUID(as_uuid=True), ForeignKey("importers.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    description_he = Column(Text, nullable=True)
    is_default_cost = Column(Boolean, nullable=False, default=False)

    ingredient = relationship("Ingredient", back_populates="bottles")
    supplier = relationship("Supplier", back_populates="bottles")
    importer = relationship("Importer", back_populates="bottles")
    prices = relationship("BottlePrice", back_populates="bottle", cascade="all, delete-orphan")

    @property
    def to_schema(self):
        return {
            "id": self.id,
            "ingredient_id": self.ingredient_id,
            "supplier_id": self.supplier_id,
            "name": self.name,
            "name_he": self.name_he,
            "volume_ml": self.volume_ml,
            "importer_id": self.importer_id,
            "description": self.description,
            "description_he": self.description_he,
            "is_default_cost": bool(self.is_default_cost),
        }

