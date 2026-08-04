from datetime import UTC, datetime, timedelta

from app.providers.base import MarketBar, MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    name = "mock"

    async def fetch_bars(self, symbol: str, limit: int = 100) -> list[MarketBar]:
        return await self.fetch_bars_interval(symbol, limit, "1day")

    async def fetch_bars_interval(
        self,
        symbol: str,
        limit: int = 100,
        interval: str = "1day",
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[MarketBar]:
        interval_steps = {
            "1min": timedelta(minutes=1),
            "5min": timedelta(minutes=5),
            "15min": timedelta(minutes=15),
            "30min": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "2h": timedelta(hours=2),
            "4h": timedelta(hours=4),
            "8h": timedelta(hours=8),
            "1day": timedelta(days=1),
        }
        step = interval_steps.get(interval, timedelta(days=1))
        count = max(1, min(limit, 2000))
        end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        anchor = end - step * 1999
        start_index = 2000 - count
        base = 100.0 + sum(ord(character) for character in symbol.upper()) % 50
        bars = [
            MarketBar(
                timestamp=anchor + step * index,
                open=base + index,
                high=base + index + 1.5,
                low=base + index - 1.0,
                close=base + index + 0.5,
                adjusted_close=base + index + 0.5,
                volume=1_000_000 + index * 1_000,
                interval=interval,
            )
            for index in range(start_index, 2000)
        ]
        return [
            bar
            for bar in bars
            if (start_at is None or bar.timestamp >= start_at)
            and (end_at is None or bar.timestamp <= end_at)
        ]
