from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "InvestVantage"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/investvantage.db"
    market_data_provider: str = "mock"
    market_data_timeout_seconds: float = 10.0
    market_data_max_retries: int = 2
    trading_mode: str = "paper"
    enable_broker_orders: bool = False
    finnhub_api_key: str | None = Field(default=None, repr=False)
    twelve_data_api_key: str | None = Field(default=None, repr=False)
    telegram_bot_token: str | None = Field(default=None, repr=False)
    jwt_secret: str | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def validate_market_data_provider(self) -> "Settings":
        allowed = {"mock", "finnhub", "twelve_data"}
        if self.market_data_provider.lower() not in allowed:
            raise ValueError(f"MARKET_DATA_PROVIDER must be one of: {', '.join(sorted(allowed))}")
        if self.market_data_timeout_seconds <= 0 or self.market_data_max_retries < 0:
            raise ValueError("Market-data timeout must be positive and retries cannot be negative")
        return self

    @model_validator(mode="after")
    def enforce_paper_trading_boundary(self) -> "Settings":
        if self.trading_mode.lower() != "paper" or self.enable_broker_orders:
            raise ValueError("Milestone 1 supports paper trading with broker orders disabled only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
