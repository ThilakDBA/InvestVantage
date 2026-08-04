from app.core.config import Settings
from app.providers.base import MarketDataConfigurationError, MarketDataProvider
from app.providers.finnhub import FinnhubMarketDataProvider
from app.providers.http import ResilientJsonClient
from app.providers.mock import MockMarketDataProvider
from app.providers.twelve_data import TwelveDataMarketDataProvider


def create_market_data_provider(settings: Settings, name: str | None = None) -> MarketDataProvider:
    provider_name = (name or settings.market_data_provider).lower()
    if provider_name == "mock":
        return MockMarketDataProvider()
    client = ResilientJsonClient(
        timeout_seconds=settings.market_data_timeout_seconds,
        max_retries=settings.market_data_max_retries,
    )
    if provider_name == "finnhub":
        return FinnhubMarketDataProvider(settings.finnhub_api_key, client)
    if provider_name == "twelve_data":
        return TwelveDataMarketDataProvider(settings.twelve_data_api_key, client)
    raise MarketDataConfigurationError("Unsupported market-data provider")
