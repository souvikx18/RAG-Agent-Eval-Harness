import os
from typing import Optional, Set
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DEV_JWT_SECRET = (
    "sTogt9rF1witiBESbB39COzyNFCp1wMaEQz4GYkpXOwwZxEP7vLe088VsjZkppVjv86HeLKbLECC-8ksBOK59A"
)

ALLOWED_ENVIRONMENTS: Set[str] = {
    "development",
    "dev",
    "test",
    "testing",
    "staging",
    "production",
    "prod",
}

ALLOWED_JWT_ALGORITHMS: Set[str] = {
    "HS256",
    "HS384",
    "HS512",
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
}


class ConfigurationError(ValueError):
    """Raised when runtime environment configuration is missing, invalid, or insecure."""
    pass


class Settings:
    DEFAULT_DEV_JWT_SECRET: str = DEFAULT_DEV_JWT_SECRET
    ALLOWED_ENVIRONMENTS: Set[str] = ALLOWED_ENVIRONMENTS
    ALLOWED_JWT_ALGORITHMS: Set[str] = ALLOWED_JWT_ALGORITHMS

    APP_NAME: str
    APP_VERSION: str
    ENVIRONMENT: str
    DEBUG: bool
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    def __init__(
        self,
        app_name: Optional[str] = None,
        app_version: Optional[str] = None,
        environment: Optional[str] = None,
        debug: Optional[bool] = None,
        database_url: Optional[str] = None,
        jwt_secret_key: Optional[str] = None,
        jwt_algorithm: Optional[str] = None,
        jwt_access_token_expire_minutes: Optional[int] = None,
        auto_validate: bool = False,
        **kwargs,
    ):
        self.APP_NAME = (
            app_name
            if app_name is not None
            else kwargs.get("APP_NAME", os.getenv("APP_NAME", "Veridyn"))
        )
        self.APP_VERSION = (
            app_version
            if app_version is not None
            else kwargs.get("APP_VERSION", os.getenv("APP_VERSION", "1.0.0"))
        )
        self.ENVIRONMENT = (
            environment
            if environment is not None
            else kwargs.get("ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
        )

        raw_debug = (
            debug
            if debug is not None
            else kwargs.get("DEBUG", os.getenv("DEBUG", "false"))
        )
        if isinstance(raw_debug, bool):
            self.DEBUG = raw_debug
        elif isinstance(raw_debug, str):
            self.DEBUG = raw_debug.strip().lower() in ("true", "1", "yes")
        else:
            self.DEBUG = bool(raw_debug)

        self.DATABASE_URL = (
            database_url
            if database_url is not None
            else kwargs.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
        )

        secret = (
            jwt_secret_key
            if jwt_secret_key is not None
            else kwargs.get(
                "JWT_SECRET_KEY",
                kwargs.get(
                    "JWT_SECRET",
                    os.getenv("JWT_SECRET_KEY")
                    or os.getenv("JWT_SECRET")
                    or DEFAULT_DEV_JWT_SECRET,
                ),
            )
        )
        self.JWT_SECRET_KEY = secret

        self.JWT_ALGORITHM = (
            jwt_algorithm
            if jwt_algorithm is not None
            else kwargs.get("JWT_ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256"))
        )

        raw_expire = (
            jwt_access_token_expire_minutes
            if jwt_access_token_expire_minutes is not None
            else kwargs.get(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"),
            )
        )
        try:
            self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(raw_expire)
        except (ValueError, TypeError):
            raise ConfigurationError(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a valid integer."
            )

        if auto_validate:
            self.validate()

    @property
    def JWT_SECRET(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("production", "prod")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("development", "dev")

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("test", "testing")

    def validate(self) -> None:
        """Validate configuration parameters according to the active environment.

        Ensures safe production defaults and rejects missing, weak, or invalid settings.
        Never leaks sensitive secret values in raised exception messages.
        """
        # Validate ENVIRONMENT
        if not self.ENVIRONMENT or self.ENVIRONMENT.strip().lower() not in self.ALLOWED_ENVIRONMENTS:
            raise ConfigurationError(
                f"ENVIRONMENT '{self.ENVIRONMENT}' is invalid. "
                f"Allowed environments are: {', '.join(sorted(self.ALLOWED_ENVIRONMENTS))}."
            )

        # Validate DATABASE_URL
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            raise ConfigurationError("DATABASE_URL must be configured.")

        # In production, SQLite in-memory databases are not permitted
        if self.is_production and self.DATABASE_URL.strip().startswith("sqlite:///:memory:"):
            raise ConfigurationError(
                "In-memory SQLite database is not permitted in production."
            )

        # Validate DEBUG in production
        if self.is_production and self.DEBUG:
            raise ConfigurationError("DEBUG mode must be disabled in production.")

        # Validate JWT_SECRET_KEY
        if not self.JWT_SECRET_KEY or not self.JWT_SECRET_KEY.strip():
            raise ConfigurationError("JWT_SECRET_KEY must not be empty.")

        if self.is_production:
            if self.JWT_SECRET_KEY == self.DEFAULT_DEV_JWT_SECRET:
                raise ConfigurationError(
                    "JWT_SECRET_KEY cannot use the default development secret in production."
                )
            if len(self.JWT_SECRET_KEY) < 32:
                raise ConfigurationError(
                    "JWT_SECRET_KEY must be at least 32 characters long in production."
                )

        # Validate JWT_ALGORITHM
        if not self.JWT_ALGORITHM or self.JWT_ALGORITHM.upper() not in self.ALLOWED_JWT_ALGORITHMS:
            raise ConfigurationError(
                f"JWT_ALGORITHM '{self.JWT_ALGORITHM}' is unsupported. "
                f"Allowed algorithms are: {', '.join(sorted(self.ALLOWED_JWT_ALGORITHMS))}."
            )

        # Validate JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        if not isinstance(self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, int) or self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ConfigurationError(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer."
            )


settings = Settings()
