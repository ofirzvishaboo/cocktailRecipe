import uuid
from sqlalchemy import Column, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Ingredient(Base):
    """Ingredient model - reusable ingredients with unique id and name"""
    __tablename__ = "ingredients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)  # Unique ingredient names

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

    # Property to convert model to schema dictionary
    @property
    def to_schema(self):
        """Convert Ingredient model to schema dictionary format"""
        return {
            "id": self.id,
            "name": self.name
        }

