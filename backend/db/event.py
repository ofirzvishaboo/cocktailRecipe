import uuid
from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    event_date = Column(Date, nullable=False, index=True)
    people = Column(Integer, nullable=False)
    servings_per_person = Column(Numeric(6, 2), nullable=False, default=3.0)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    menu_items = relationship("EventMenuItem", back_populates="event", cascade="all, delete-orphan")


class EventMenuItem(Base):
    __tablename__ = "event_menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    cocktail_recipe_id = Column(UUID(as_uuid=True), ForeignKey("cocktail_recipes.id", ondelete="CASCADE"), nullable=False, index=True)

    event = relationship("Event", back_populates="menu_items")
    cocktail = relationship("CocktailRecipe")

