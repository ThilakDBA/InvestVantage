from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models import Instrument, WatchlistItem
from app.services.watchlists import load_watchlist_file, upsert_watchlist


def test_watchlist_file_load_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.yml"
    path.write_text(
        """name: Pilot
instruments:
  - symbol: AAPL
    exchange: NASDAQ
    name: Apple Inc.
    asset_type: STOCK
""",
        encoding="utf-8",
    )
    request = load_watchlist_file(path)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        upsert_watchlist(session, request)
        upsert_watchlist(session, request)
        instrument_count = session.scalar(select(func.count()).select_from(Instrument))
        item_count = session.scalar(select(func.count()).select_from(WatchlistItem))
    assert instrument_count == 1
    assert item_count == 1
