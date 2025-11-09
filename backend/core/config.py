import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/cocktaildb"
    )
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"


settings = Settings()
