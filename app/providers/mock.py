from datetime import UTC, datetime, timedelta

from app.providers.base import MarketBar, MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    name = "mock"

    async def fetch_bars(self, symbol: str, limit: int = 100) -> list[MarketBar]:
        count = max(1, min(limit, 100))
        anchor = datetime(2026, 1, 2, tzinfo=UTC)
        base = 100.0 + sum(ord(character) for character in symbol.upper()) % 50
        return [
            MarketBar(
                timestamp=anchor + timedelta(days=index),
                open=base + index,
                high=base + index + 1.5,
                low=base + index - 1.0,
                close=base + index + 0.5,
                adjusted_close=base + index + 0.5,
                volume=1_000_000 + index * 1_000,
            )
            for index in range(count)
        ]
