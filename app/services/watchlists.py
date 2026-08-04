from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Instrument, Watchlist, WatchlistItem
from app.schemas.market import InstrumentCreate, WatchlistCreate


class WatchlistFile(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    instruments: list[InstrumentCreate]


def load_watchlist_file(path: Path) -> WatchlistCreate:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        parsed = WatchlistFile.model_validate(payload)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"Invalid watchlist file: {path}") from exc
    return WatchlistCreate(**parsed.model_dump())


def upsert_watchlist(session: Session, request: WatchlistCreate) -> Watchlist:
    watchlist = session.scalar(select(Watchlist).where(Watchlist.name == request.name))
    if watchlist is None:
        watchlist = Watchlist(name=request.name, description=request.description)
        session.add(watchlist)
        session.flush()
    else:
        watchlist.description = request.description

    for item in request.instruments:
        symbol = item.symbol.upper()
        exchange = item.exchange.upper()
        instrument = session.scalar(
            select(Instrument).where(
                Instrument.symbol == symbol,
                Instrument.exchange == exchange,
            )
        )
        if instrument is None:
            instrument_data = item.model_dump()
            instrument_data.update(symbol=symbol, exchange=exchange)
            instrument = Instrument(**instrument_data)
            session.add(instrument)
            session.flush()
        existing_item = session.scalar(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist.id,
                WatchlistItem.instrument_id == instrument.id,
            )
        )
        if existing_item is None:
            session.add(WatchlistItem(watchlist_id=watchlist.id, instrument_id=instrument.id))
    session.commit()
    session.refresh(watchlist)
    return watchlist
