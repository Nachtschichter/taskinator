"""
Taskinator Application Configuration

Provides centralized, environment-driven configuration.
NO hardcoded URLs or secrets in this module.
"""
import os

class Config:
    """
    Application configuration assembled strictly from environment variables.
    """
    # --- URL Construction ---
    PROTOCOL: str = os.getenv("PROTOCOL", "http")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "9900"))

    @property
    def base_url(self) -> str:
        """Dynamically constructed application base URL."""
        return f"{self.PROTOCOL}://{self.HOST}:{self.PORT}"

    # --- Security ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:////app/data/taskinator.db"
    )

    # --- Admin Bootstrap ---
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

    # --- JWT ---
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    def validate(self) -> None:
        """
        Runtime validation to prevent startup with unsafe defaults.
        Raises RuntimeError if critical configuration is missing or weak.
        """
        default_secret = "taskinator-production-secret-key-change-me"
        if not self.SECRET_KEY or self.SECRET_KEY == default_secret:
            raise RuntimeError(
                "FATAL: SECRET_KEY is not set or is the default value. "
                "Set a strong, unique SECRET_KEY environment variable before starting the application."
            )
        if self.ADMIN_PASSWORD and len(self.ADMIN_PASSWORD) < 8:
            raise RuntimeError(
                "FATAL: ADMIN_PASSWORD is set but shorter than 8 characters."
            )

# Global singleton for import convenience
config = Config()
