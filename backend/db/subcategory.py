import uuid
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Subcategory(Base):
    __tablename__ = "subcategories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind_id = Column(UUID(as_uuid=True), ForeignKey("kinds.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    name_he = Column(String, nullable=True)

    kind = relationship("Kind", back_populates="subcategories")
    ingredients = relationship("Ingredient", back_populates="subcategory")

