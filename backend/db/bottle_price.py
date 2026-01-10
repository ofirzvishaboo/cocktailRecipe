import uuid
from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class BottlePrice(Base):
    __tablename__ = "bottle_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bottle_id = Column(UUID(as_uuid=True), ForeignKey("bottles.id", ondelete="CASCADE"), nullable=False, index=True)

    price_minor = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="ILS")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    source = Column(Text, nullable=True)

    bottle = relationship("Bottle", back_populates="prices")

