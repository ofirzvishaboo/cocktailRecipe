import uuid
from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(Text, nullable=False, default="WEEKLY", index=True)  # WEEKLY|EVENT
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(Text, nullable=False, default="DRAFT", index=True)  # DRAFT|SENT|RECEIVED|CANCELLED
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    supplier = relationship("Supplier")
    event = relationship("Event")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)

    # Before-stock (requested) amounts
    requested_ml = Column(Numeric, nullable=True)
    requested_quantity = Column(Numeric, nullable=True)
    requested_unit = Column(String, nullable=True)

    # Stock allocation for the scope (event allocation is sequential across events)
    used_from_stock_ml = Column(Numeric, nullable=True)
    used_from_stock_quantity = Column(Numeric, nullable=True)

    # After-stock shortfall (what must be ordered)
    needed_ml = Column(Numeric, nullable=True)
    needed_quantity = Column(Numeric, nullable=True)
    unit = Column(String, nullable=True)

    bottle_id = Column(UUID(as_uuid=True), ForeignKey("bottles.id", ondelete="SET NULL"), nullable=True, index=True)
    bottle_volume_ml = Column(Integer, nullable=True)
    recommended_bottles = Column(Integer, nullable=True)
    leftover_ml = Column(Numeric, nullable=True)

    order = relationship("Order", back_populates="items")
    ingredient = relationship("Ingredient")
    bottle = relationship("Bottle")

