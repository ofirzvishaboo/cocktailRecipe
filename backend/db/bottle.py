import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Bottle(Base):
    __tablename__ = "bottles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String, nullable=False)
    name_he = Column(String, nullable=True)
    volume_ml = Column(Integer, nullable=False)
    importer_id = Column(UUID(as_uuid=True), ForeignKey("importers.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    description_he = Column(Text, nullable=True)
    is_default_cost = Column(Boolean, nullable=False, default=False)

    ingredient = relationship("Ingredient", back_populates="bottles")
    importer = relationship("Importer", back_populates="bottles")
    prices = relationship("BottlePrice", back_populates="bottle", cascade="all, delete-orphan")

