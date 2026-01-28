from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from .database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    cocktails = relationship("CocktailRecipe", back_populates="user", cascade="all, delete-orphan")
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)


    @property
    def to_schema(self):
        """Convert User model to schema dictionary format"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": getattr(self, "first_name", None),
            "last_name": getattr(self, "last_name", None),
        }



