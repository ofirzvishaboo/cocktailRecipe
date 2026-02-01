import uuid

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location = Column(Text, nullable=False, index=True)  # 'BAR' | 'WAREHOUSE'

    inventory_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    change = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    source_type = Column(Text, nullable=True)
    source_id = Column(BigInteger, nullable=True)
    source_event_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    is_reversal = Column(Boolean, nullable=False, default=False)
    is_reversed = Column(Boolean, nullable=False, default=False)
    reversal_of_id = Column(UUID(as_uuid=True), ForeignKey("inventory_movements.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    inventory_item = relationship("InventoryItem", back_populates="movements")
    created_by_user = relationship("User")

