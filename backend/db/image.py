import uuid
from sqlalchemy import Column, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class Image(Base):
    """Stored image binary for cocktail pictures (replaces ImageKit)."""
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(LargeBinary, nullable=False)
    content_type = Column(String(255), nullable=False)
