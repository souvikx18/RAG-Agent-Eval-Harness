from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Veridyn")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()