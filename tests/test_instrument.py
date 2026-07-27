from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.models import Instrument


def test_instrument_can_be_persisted() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Instrument(
                symbol="SPY",
                exchange="NYSEARCA",
                name="SPDR S&P 500 ETF Trust",
                asset_type="ETF",
                sector=None,
            )
        )
        session.commit()
        instrument = session.scalar(select(Instrument))

    assert instrument is not None
    assert instrument.symbol == "SPY"
    assert instrument.currency == "USD"
    assert instrument.is_active is True
