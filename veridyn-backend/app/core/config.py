from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Veridyn")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "sTogt9rF1witiBESbB39COzyNFCp1wMaEQz4GYkpXOwwZxEP7vLe088VsjZkppVjv86HeLKbLECC-8ksBOK59A")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )


settings = Settings()