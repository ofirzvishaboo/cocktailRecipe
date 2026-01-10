import uuid
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class GlassType(Base):
    __tablename__ = "glass_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    capacity_ml = Column(Integer, nullable=True)

    recipes = relationship("CocktailRecipe", back_populates="glass_type")

