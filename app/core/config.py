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
    trading_mode: str = "paper"
    enable_broker_orders: bool = False
    finnhub_api_key: str | None = Field(default=None, repr=False)
    twelve_data_api_key: str | None = Field(default=None, repr=False)
    telegram_bot_token: str | None = Field(default=None, repr=False)
    jwt_secret: str | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def enforce_paper_trading_boundary(self) -> "Settings":
        if self.trading_mode.lower() != "paper" or self.enable_broker_orders:
            raise ValueError("Milestone 1 supports paper trading with broker orders disabled only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
