from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MarketBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None = None
    volume: int | None = None
    interval: str = "1day"


class MarketDataError(RuntimeError):
    """A safe provider error suitable for API responses and logs."""


class MarketDataConfigurationError(MarketDataError):
    pass


class MarketDataRateLimitError(MarketDataError):
    pass


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    async def fetch_bars(self, symbol: str, limit: int = 100) -> list[MarketBar]:
        """Return normalized bars ordered from oldest to newest."""

    async def fetch_bars_interval(
        self,
        symbol: str,
        limit: int = 100,
        interval: str = "1day",
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[MarketBar]:
        if interval != "1day":
            raise MarketDataError(f"{self.name} does not support interval {interval}")
        return await self.fetch_bars(symbol, limit)
