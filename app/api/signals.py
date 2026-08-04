from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.analysis import analyse_bars
from app.database.models import Instrument, PriceHistory, Signal
from app.providers import create_market_data_provider
from app.providers.base import MarketBar, MarketDataError
from app.schemas.signals import SignalGenerateRequest, SignalResponse
from app.services.market_data import fetch_and_store
from app.strategies import generate_decision

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


def _response(signal: Signal) -> SignalResponse:
    return SignalResponse(
        **{column.name: getattr(signal, column.name) for column in Signal.__table__.columns},
        symbol=signal.instrument.symbol,
    )


def _bars(session, instrument_id: int, provider: str) -> list[MarketBar]:
    rows = session.scalars(
        select(PriceHistory)
        .where(
            PriceHistory.instrument_id == instrument_id,
            PriceHistory.data_source == provider,
        )
        .order_by(PriceHistory.timestamp)
    )
    return [
        MarketBar(
            row.timestamp,
            row.open,
            row.high,
            row.low,
            row.close,
            row.adjusted_close,
            row.volume,
            row.interval,
        )
        for row in rows
    ]


@router.post("/generate", response_model=list[SignalResponse])
async def generate_signals(
    payload: SignalGenerateRequest, request: Request
) -> list[SignalResponse]:
    provider = create_market_data_provider(request.app.state.settings, payload.provider)
    generated = []
    with request.app.state.database.session_factory() as session:
        for symbol in dict.fromkeys(value.upper() for value in payload.symbols):
            instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol))
            if instrument is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrument not found: {symbol}")
            try:
                await fetch_and_store(session, provider, instrument, payload.limit)
            except MarketDataError as exc:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
            bars = _bars(session, instrument.id, provider.name)
            if len(bars) < 35:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "At least 35 price bars are required",
                )
            analysis = analyse_bars(bars)
            decision = generate_decision(analysis, bars[-1].close)
            now = datetime.now(UTC)
            completeness = round(
                sum(
                    value is not None
                    for value in (
                        analysis.sma_20,
                        analysis.sma_50,
                        analysis.rsi_14,
                        analysis.macd_signal,
                        analysis.atr_14,
                    )
                )
                / 5
                * 100
            )
            signal = Signal(
                instrument_id=instrument.id,
                strategy_name="Quality Momentum Swing",
                strategy_version="1.0",
                recommendation=decision.recommendation,
                technical_score=analysis.score,
                confidence_score=decision.confidence_score,
                risk_score=decision.risk_score,
                entry_price=decision.entry_price,
                stop_price=decision.stop_price,
                target_price=decision.target_price,
                holding_period_days=20,
                explanation=decision.explanation,
                positive_factors=analysis.positive_factors,
                negative_factors=analysis.negative_factors,
                invalidation_conditions=decision.invalidation_conditions,
                data_completeness=completeness,
                generated_at=now,
                expires_at=now + timedelta(days=30),
            )
            session.add(signal)
            session.flush()
            signal.instrument = instrument
            generated.append(signal)
        session.commit()
        return [_response(signal) for signal in generated]


@router.get("", response_model=list[SignalResponse])
def list_signals(request: Request) -> list[SignalResponse]:
    with request.app.state.database.session_factory() as session:
        signals = session.scalars(
            select(Signal)
            .options(selectinload(Signal.instrument))
            .order_by(Signal.generated_at.desc())
            .limit(100)
        )
        return [_response(signal) for signal in signals]


@router.get("/latest/{symbol}", response_model=SignalResponse)
def latest_signal(symbol: str, request: Request) -> SignalResponse:
    with request.app.state.database.session_factory() as session:
        signal = session.scalar(
            select(Signal)
            .join(Instrument)
            .where(Instrument.symbol == symbol.upper())
            .options(selectinload(Signal.instrument))
            .order_by(Signal.generated_at.desc())
        )
        if signal is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Signal not found")
        return _response(signal)
