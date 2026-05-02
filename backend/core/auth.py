import uuid
from fastapi import Depends
from fastapi_users import FastAPIUsers, BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from db.users import User
from db.database import get_user_db
import os
from dotenv import load_dotenv

load_dotenv()

_raw_secret = os.getenv("SECRET", "")
if not _raw_secret or _raw_secret == "SECRET":
    raise RuntimeError(
        "SECRET environment variable is not set or is using the insecure default. "
        "Set a random string of at least 32 characters before starting the server."
    )
if len(_raw_secret) < 32:
    raise RuntimeError(
        f"SECRET environment variable is too short ({len(_raw_secret)} chars). "
        "Use at least 32 random characters."
    )
SECRET = _raw_secret
JWT_LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", "604800"))  # default: 7 days


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET


async def get_user_manager(user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db)):
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=JWT_LIFETIME_SECONDS)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
current_active_superuser = fastapi_users.current_user(active=True, superuser=True)

