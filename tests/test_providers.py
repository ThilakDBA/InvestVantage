from datetime import UTC

import pytest

from app.providers.base import MarketDataError
from app.providers.finnhub import FinnhubMarketDataProvider
from app.providers.twelve_data import TwelveDataMarketDataProvider


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def get(self, *args, **kwargs) -> dict:
        return self.payload


@pytest.mark.asyncio
async def test_finnhub_quote_is_normalized() -> None:
    provider = FinnhubMarketDataProvider(
        "secret",
        FakeClient({"c": 190.5, "o": 189, "h": 191, "l": 188, "t": 1_700_000_000}),
    )
    bars = await provider.fetch_bars("aapl")
    assert bars[0].close == 190.5
    assert bars[0].interval == "quote"


@pytest.mark.asyncio
async def test_twelve_data_history_is_normalized_to_utc() -> None:
    provider = TwelveDataMarketDataProvider(
        "secret",
        FakeClient(
            {
                "meta": {"exchange_timezone": "America/New_York"},
                "values": [
                    {
                        "datetime": "2026-01-02 09:30:00",
                        "open": "100",
                        "high": "102",
                        "low": "99",
                        "close": "101",
                        "volume": "1000",
                    }
                ],
                "status": "ok",
            }
        ),
    )
    bars = await provider.fetch_bars("AAPL")
    assert bars[0].timestamp.tzinfo == UTC
    assert bars[0].volume == 1000


@pytest.mark.asyncio
async def test_twelve_data_intraday_interval_is_preserved() -> None:
    provider = TwelveDataMarketDataProvider(
        "secret",
        FakeClient(
            {
                "meta": {"exchange_timezone": "America/New_York"},
                "values": [
                    {
                        "datetime": "2026-01-02 09:35:00",
                        "open": "100",
                        "high": "102",
                        "low": "99",
                        "close": "101",
                        "volume": "1000",
                    }
                ],
                "status": "ok",
            }
        ),
    )
    bars = await provider.fetch_bars_interval("AAPL", interval="5min")
    assert bars[0].interval == "5min"
    assert bars[0].timestamp.hour == 9


@pytest.mark.asyncio
async def test_twelve_data_error_does_not_expose_key() -> None:
    provider = TwelveDataMarketDataProvider(
        "do-not-leak", FakeClient({"status": "error", "message": "Invalid symbol"})
    )
    with pytest.raises(MarketDataError, match="Invalid symbol") as error:
        await provider.fetch_bars("BAD")
    assert "do-not-leak" not in str(error.value)
