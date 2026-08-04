from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.providers.base import (
    MarketBar,
    MarketDataConfigurationError,
    MarketDataError,
    MarketDataProvider,
)
from app.providers.http import ResilientJsonClient


class TwelveDataMarketDataProvider(MarketDataProvider):
    name = "twelve_data"
    url = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key: str | None, client: ResilientJsonClient) -> None:
        self.api_key = api_key
        self.client = client

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
        if not self.api_key:
            raise MarketDataConfigurationError("Twelve Data API key is not configured")
        allowed_intervals = {"1min", "5min", "15min", "30min", "1h", "2h", "4h", "8h", "1day"}
        if interval not in allowed_intervals:
            raise MarketDataError(f"Unsupported Twelve Data interval: {interval}")
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "outputsize": max(1, min(limit, 5000)),
            "order": "asc",
            "timezone": "UTC",
        }
        if start_at:
            params["start_date"] = start_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        if end_at:
            params["end_date"] = end_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        payload = await self.client.get(
            self.url,
            params=params,
            headers={"Authorization": f"apikey {self.api_key}"},
        )
        if payload.get("status") == "error":
            raise MarketDataError(str(payload.get("message") or "Twelve Data request failed"))
        values = payload.get("values")
        if not isinstance(values, list):
            raise MarketDataError("Twelve Data returned no price history for this symbol")
        timezone = ZoneInfo("UTC") if interval != "1day" else self._timezone(payload)
        bars = [self._parse_bar(value, timezone, interval) for value in values]
        return sorted(bars, key=lambda bar: bar.timestamp)

    @staticmethod
    def _timezone(payload: dict) -> ZoneInfo:
        timezone_name = (payload.get("meta") or {}).get("exchange_timezone", "UTC")
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _parse_bar(value: dict, timezone: ZoneInfo, interval: str = "1day") -> MarketBar:
        try:
            timestamp = datetime.fromisoformat(str(value["datetime"])).replace(tzinfo=timezone)
            return MarketBar(
                timestamp=timestamp.astimezone(UTC),
                open=float(value["open"]),
                high=float(value["high"]),
                low=float(value["low"]),
                close=float(value["close"]),
                adjusted_close=float(value["close"]),
                volume=int(value["volume"]) if value.get("volume") is not None else None,
                interval=interval,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MarketDataError("Twelve Data returned a malformed price bar") from exc
