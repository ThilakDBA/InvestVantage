from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Instrument, PriceHistory
from app.providers.base import MarketBar, MarketDataProvider


async def fetch_and_store(
    session: Session,
    provider: MarketDataProvider,
    instrument: Instrument,
    limit: int,
) -> tuple[list[MarketBar], int]:
    bars = await provider.fetch_bars(instrument.symbol, limit)
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
