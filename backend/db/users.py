from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.orm import relationship
from .database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    cocktail = relationship("CocktailRecipe", back_populates="user")
    __tablename__ = "users"
    

    @property
    def to_schema(self):
        """Convert User model to schema dictionary format"""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username
        }



