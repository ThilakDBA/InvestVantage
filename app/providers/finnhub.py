from datetime import UTC, datetime

from app.providers.base import (
    MarketBar,
    MarketDataConfigurationError,
    MarketDataError,
    MarketDataProvider,
)
from app.providers.http import ResilientJsonClient


class FinnhubMarketDataProvider(MarketDataProvider):
    """Finnhub quote adapter; historical candles may require a paid plan."""

    name = "finnhub"
    url = "https://finnhub.io/api/v1/quote"

    def __init__(self, api_key: str | None, client: ResilientJsonClient) -> None:
        self.api_key = api_key
        self.client = client

    async def fetch_bars(self, symbol: str, limit: int = 100) -> list[MarketBar]:
        if not self.api_key:
            raise MarketDataConfigurationError("Finnhub API key is not configured")
        payload = await self.client.get(
            self.url,
            params={"symbol": symbol.upper()},
            headers={"X-Finnhub-Token": self.api_key},
        )
        current = float(payload.get("c") or 0)
        timestamp = int(payload.get("t") or 0)
        if current <= 0 or timestamp <= 0:
            raise MarketDataError("Finnhub returned no quote for this symbol")
        return [
            MarketBar(
                timestamp=datetime.fromtimestamp(timestamp, tz=UTC),
                open=float(payload.get("o") or current),
                high=float(payload.get("h") or current),
                low=float(payload.get("l") or current),
                close=current,
                interval="quote",
            )
        ]
