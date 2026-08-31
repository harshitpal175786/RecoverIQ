from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # OpenRouter / LLM
    OPENROUTER_API_KEY: str = "your_key_here"
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-exp:free"
    OPENROUTER_FALLBACK_MODELS: str = "deepseek/deepseek-chat,meta-llama/llama-3.3-70b-instruct:free"
    LLM_CONFIDENCE_THRESHOLD: float = 0.6
    LLM_TIMEOUT_SECONDS: int = 30

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_xxx"
    RAZORPAY_KEY_SECRET: str = "your_secret_here"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./recoveriq.db"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Recovery Logic
    MAX_RETRIES: int = 2
    COOLDOWN_MINUTES: int = 5
    HIGH_VALUE_THRESHOLD_INR: int = 50000
    RECOVERY_WINDOW_HOURS: int = 72
    QUIET_HOURS_START: int = 21
    QUIET_HOURS_END: int = 8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def fallback_models_list(self) -> List[str]:
        """Return the fallback models as a list of strings."""
        if not self.OPENROUTER_FALLBACK_MODELS:
            return []
        return [m.strip() for m in self.OPENROUTER_FALLBACK_MODELS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get the cached settings instance."""
    return Settings()
