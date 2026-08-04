from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.database.models import Instrument, ResearchSnapshot
from app.providers.base import MarketDataError
from app.providers.finnhub_research import (
    FinnhubResearchProvider,
    fundamental_score,
    news_score,
    source_timestamp,
)
from app.providers.http import ResilientJsonClient
from app.schemas.research import ResearchComponent, ResearchResponse

router = APIRouter(prefix="/api/v1/research", tags=["research intelligence"])


def _provider(request: Request) -> FinnhubResearchProvider:
    settings = request.app.state.settings
    return FinnhubResearchProvider(
        settings.finnhub_api_key,
        ResilientJsonClient(settings.market_data_timeout_seconds, settings.market_data_max_retries),
    )


def _upsert(session, instrument_id: int, data_type: str, payload, score: int | None) -> None:
    snapshot = session.scalar(
        select(ResearchSnapshot).where(
            ResearchSnapshot.instrument_id == instrument_id,
            ResearchSnapshot.data_type == data_type,
            ResearchSnapshot.provider == "finnhub",
        )
    )
    timestamp = source_timestamp(payload[0]) if isinstance(payload, list) and payload else None
    if snapshot is None:
        snapshot = ResearchSnapshot(
            instrument_id=instrument_id,
            data_type=data_type,
            provider="finnhub",
            payload=payload,
        )
        session.add(snapshot)
    snapshot.payload = payload
    snapshot.score = score
    snapshot.source_timestamp = timestamp
    snapshot.retrieved_at = datetime.now(UTC)


async def refresh_research(request: Request, instrument: Instrument) -> None:
    provider = _provider(request)
    fundamentals = await provider.fundamentals(instrument.symbol)
    news = await provider.news(instrument.symbol)
    earnings = await provider.earnings(instrument.symbol)
    fundamental_value, _, _ = fundamental_score(fundamentals)
    news_value, _, _ = news_score(news)
    with request.app.state.database.session_factory() as session:
        _upsert(session, instrument.id, "fundamentals", fundamentals, fundamental_value)
        _upsert(session, instrument.id, "news", news, news_value)
        _upsert(session, instrument.id, "earnings", earnings, None)
        session.commit()


def _component(snapshot: ResearchSnapshot | None, factors=None, risks=None) -> ResearchComponent:
    return ResearchComponent(
        score=snapshot.score if snapshot else None,
        available=snapshot is not None,
        provider=snapshot.provider if snapshot else "not_available",
        retrieved_at=snapshot.retrieved_at if snapshot else None,
        factors=factors or [],
        risks=risks or [],
        data=snapshot.payload if snapshot else {},
    )


@router.get("/{symbol}", response_model=ResearchResponse)
async def get_research(
    symbol: str, request: Request, refresh: bool = Query(default=False)
) -> ResearchResponse:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
    if instrument is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
    if refresh:
        try:
            await refresh_research(request, instrument)
        except MarketDataError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    with request.app.state.database.session_factory() as session:
        rows = session.scalars(
            select(ResearchSnapshot).where(ResearchSnapshot.instrument_id == instrument.id)
        ).all()
        values = {row.data_type: row for row in rows}
        fundamental = values.get("fundamentals")
        news = values.get("news")
        f_score, f_factors, f_risks = (
            fundamental_score(fundamental.payload) if fundamental else (0, [], [])
        )
        n_score, n_factors, n_risks = news_score(news.payload) if news else (0, [], [])
        if fundamental:
            fundamental.score = f_score
        if news:
            news.score = n_score
        completeness = round(
            sum(key in values for key in ("fundamentals", "news", "earnings")) / 3 * 100
        )
        return ResearchResponse(
            symbol=instrument.symbol,
            fundamentals=_component(fundamental, f_factors, f_risks),
            news=_component(news, n_factors, n_risks),
            earnings=_component(values.get("earnings")),
            data_completeness=completeness,
        )
