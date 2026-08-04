from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.analysis import analyse_bars
from app.database.models import Instrument, PriceHistory
from app.providers import create_market_data_provider
from app.providers.base import MarketBar, MarketDataError
from app.schemas.analysis import (
    IndicatorValues,
    PricePoint,
    TechnicalAnalysisResponse,
)
from app.services.market_data import fetch_and_store

router = APIRouter(prefix="/api/v1/analysis", tags=["technical analysis"])


def _stored_bars(
    request: Request,
    instrument_id: int,
    provider: str,
    interval: str,
    start_at=None,
    end_at=None,
) -> list[MarketBar]:
    with request.app.state.database.session_factory() as session:
        statement = (
            select(PriceHistory)
            .where(
                PriceHistory.instrument_id == instrument_id,
                PriceHistory.data_source == provider,
                PriceHistory.interval == interval,
            )
            .order_by(PriceHistory.timestamp)
        )
        if start_at:
            statement = statement.where(PriceHistory.timestamp >= start_at)
        if end_at:
            statement = statement.where(PriceHistory.timestamp <= end_at)
        rows = session.scalars(statement)
        return [
            MarketBar(
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                adjusted_close=row.adjusted_close,
                volume=row.volume,
                interval=row.interval,
            )
            for row in rows
        ]


@router.get("/{symbol}/technical", response_model=TechnicalAnalysisResponse)
async def technical_analysis(
    symbol: str,
    request: Request,
    provider: str | None = Query(default=None),
    refresh: bool = Query(default=True),
    limit: int = Query(default=100, ge=35, le=5000),
    interval: str = Query(default="1day"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
) -> TechnicalAnalysisResponse:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
        if instrument is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
        provider_instance = create_market_data_provider(request.app.state.settings, provider)
        if refresh:
            try:
                await fetch_and_store(
                    session,
                    provider_instance,
                    instrument,
                    limit,
                    interval,
                    start_at,
                    end_at,
                )
            except MarketDataError as exc:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        instrument_id = instrument.id

    bars = _stored_bars(
        request, instrument_id, provider_instance.name, interval, start_at, end_at
    )
    if len(bars) < 35:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"At least 35 price bars are required; found {len(bars)}",
        )
    analysis = analyse_bars(bars)
    values = asdict(analysis)
    positive = values.pop("positive_factors")
    negative = values.pop("negative_factors")
    trend = values.pop("trend")
    score = values.pop("score")
    return TechnicalAnalysisResponse(
        symbol=symbol.upper(),
        provider=provider_instance.name,
        interval=interval,
        trend=trend,
        technical_score=score,
        data_points=len(bars),
        indicators=IndicatorValues(**values),
        positive_factors=positive,
        negative_factors=negative,
        price_history=[
            PricePoint(
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                interval=bar.interval,
            )
            for bar in bars[-2000:]
        ],
    )
