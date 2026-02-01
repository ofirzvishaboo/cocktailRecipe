import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    contact = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    ingredients = relationship("Ingredient", secondary="ingredient_suppliers", back_populates="suppliers")

    @property
    def to_schema(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact": self.contact,
            "notes": self.notes,
        }

