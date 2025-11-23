import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/cocktaildb"
    )
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"

    # ImageKit Settings
    imagekit_public_key: str = os.getenv("IMAGEKIT_PUBLIC_KEY", "")
    imagekit_private_key: str = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
    imagekit_url_endpoint: str = os.getenv("IMAGEKIT_URL_ENDPOINT", "")


settings = Settings()
