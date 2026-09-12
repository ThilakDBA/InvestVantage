import asyncio
import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.models import Instrument, ResearchSnapshot
from app.database.session import Database
from app.providers import create_market_data_provider
from app.providers.base import MarketDataError
from app.providers.finnhub_research import FinnhubResearchProvider, fundamental_score, news_score
from app.providers.http import ResilientJsonClient
from app.services.market_data import fetch_and_store

logger = logging.getLogger(__name__)


async def seed() -> None:
    settings = get_settings()
    database = Database(settings.database_url)
    price_provider = create_market_data_provider(settings, "twelve_data")
    research_provider = FinnhubResearchProvider(
        settings.finnhub_api_key,
        ResilientJsonClient(settings.market_data_timeout_seconds, settings.market_data_max_retries),
    )
    with database.session_factory() as session:
        instruments = session.scalars(
            select(Instrument).where(Instrument.is_active.is_(True))
        ).all()
        for instrument in instruments:
            try:
                _, stored = await fetch_and_store(session, price_provider, instrument, 500)
                logger.info("Seeded %s new price bars for %s", stored, instrument.symbol)
                if instrument.asset_type.upper() != "ETF":
                    payloads = {
                        "fundamentals": await research_provider.fundamentals(instrument.symbol),
                        "news": await research_provider.news(instrument.symbol),
                        "earnings": await research_provider.earnings(instrument.symbol),
                    }
                    for data_type, loader in (
                        ("dividends", research_provider.dividends),
                        ("splits", research_provider.splits),
                    ):
                        try:
                            payloads[data_type] = await loader(instrument.symbol)
                        except MarketDataError as exc:
                            logger.info(
                                "%s unavailable for %s: %s",
                                data_type,
                                instrument.symbol,
                                exc,
                            )
                    for data_type, payload in payloads.items():
                        score = None
                        if data_type == "fundamentals":
                            score = fundamental_score(payload)[0]
                        elif data_type == "news":
                            score = news_score(payload)[0]
                        row = session.scalar(
                            select(ResearchSnapshot).where(
                                ResearchSnapshot.instrument_id == instrument.id,
                                ResearchSnapshot.data_type == data_type,
                                ResearchSnapshot.provider == "finnhub",
                            )
                        )
                        if row is None:
                            row = ResearchSnapshot(
                                instrument_id=instrument.id,
                                data_type=data_type,
                                provider="finnhub",
                                payload=payload,
                            )
                            session.add(row)
                        row.payload = payload
                        row.score = score
                    session.commit()
            except MarketDataError as exc:
                session.rollback()
                logger.warning("Seed failed for %s: %s", instrument.symbol, exc)
    database.dispose()


if __name__ == "__main__":
    configure_logging(get_settings().log_level)
    asyncio.run(seed())
