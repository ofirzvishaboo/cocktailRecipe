import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Kind(Base):
    __tablename__ = "kinds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)

    subcategories = relationship("Subcategory", back_populates="kind", cascade="all, delete-orphan")
    ingredients = relationship("Ingredient", back_populates="kind")

