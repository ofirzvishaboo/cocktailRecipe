import uuid
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class IngredientBrand(Base):
    """Purchasable bottle SKU for an ingredient (brand + bottle size + bottle price)."""

    __tablename__ = "ingredient_brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    brand_name = Column(String, nullable=False)
    bottle_size_ml = Column(Integer, nullable=False)
    bottle_price = Column(Numeric, nullable=False)

    ingredient = relationship("Ingredient", back_populates="brands")


