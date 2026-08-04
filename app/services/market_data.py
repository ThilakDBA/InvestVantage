from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Instrument, PriceHistory
from app.providers.base import MarketBar, MarketDataError, MarketDataProvider


def validate_bars(bars: list[MarketBar], provider_name: str) -> None:
    if not bars:
        raise MarketDataError("Provider returned no price bars")
    timestamps = [bar.timestamp for bar in bars]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise MarketDataError("Price history is not uniquely ordered")
    for bar in bars:
        if min(bar.open, bar.high, bar.low, bar.close) <= 0:
            raise MarketDataError("Price history contains a non-positive OHLC value")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            raise MarketDataError("Price history contains an invalid OHLC range")
        if bar.volume is not None and bar.volume < 0:
            raise MarketDataError("Price history contains negative volume")
    latest = timestamps[-1]
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    if latest > datetime.now(UTC) + timedelta(minutes=5):
        raise MarketDataError("Price history contains a future timestamp")
    if provider_name != "mock" and latest < datetime.now(UTC) - timedelta(days=10):
        raise MarketDataError("Provider price history is stale by more than 10 calendar days")


async def fetch_and_store(
    session: Session,
    provider: MarketDataProvider,
    instrument: Instrument,
    limit: int,
    interval: str = "1day",
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> tuple[list[MarketBar], int]:
    bars = await provider.fetch_bars_interval(
        instrument.symbol, limit, interval, start_at, end_at
    )
    validate_bars(bars, provider.name)
    stored = 0
    for bar in bars:
        existing = session.scalar(
            select(PriceHistory.id).where(
                PriceHistory.instrument_id == instrument.id,
                PriceHistory.timestamp == bar.timestamp,
                PriceHistory.interval == bar.interval,
                PriceHistory.data_source == provider.name,
            )
        )
        if existing is None:
            session.add(
                PriceHistory(
                    instrument_id=instrument.id,
                    timestamp=bar.timestamp,
                    interval=bar.interval,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    adjusted_close=bar.adjusted_close,
                    volume=bar.volume,
                    data_source=provider.name,
                )
            )
            stored += 1
    session.commit()
    return bars, stored
