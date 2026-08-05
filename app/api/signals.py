from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.analysis import analyse_bars
from app.analysis.backtest import BacktestAssumptions, run_backtest
from app.analysis.context import (
    SECTOR_BENCHMARKS,
    market_regime,
    portfolio_suitability,
    relative_strength,
)
from app.database.models import (
    Instrument,
    PortfolioHolding,
    PriceHistory,
    ResearchSnapshot,
    Signal,
    SignalOutcome,
)
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


def _bars(session, instrument_id: int, provider: str, interval: str = "1day") -> list[MarketBar]:
    rows = session.scalars(
        select(PriceHistory)
        .where(
            PriceHistory.instrument_id == instrument_id,
            PriceHistory.data_source == provider,
            PriceHistory.interval == interval,
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


def _research_scores(session, instrument_id: int) -> tuple[int | None, int | None]:
    rows = session.scalars(
        select(ResearchSnapshot).where(ResearchSnapshot.instrument_id == instrument_id)
    ).all()
    now = datetime.now(UTC)
    maximum_age = {"fundamentals": timedelta(days=7), "news": timedelta(days=2)}
    scores = {}
    for row in rows:
        if row.data_type not in maximum_age or not row.retrieved_at:
            continue
        retrieved_at = row.retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=UTC)
        if now - retrieved_at <= maximum_age[row.data_type]:
            scores[row.data_type] = row.score
    return scores.get("fundamentals"), scores.get("news")


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
            fundamental, news = _research_scores(session, instrument.id)
            spy = session.scalar(select(Instrument).where(Instrument.symbol == "SPY"))
            spy_bars = _bars(session, spy.id, provider.name) if spy else []
            regime_value, regime_factor = market_regime(spy_bars)
            regime = regime_value if spy_bars else None
            sector_symbol = SECTOR_BENCHMARKS.get(instrument.sector or "")
            sector = session.scalar(select(Instrument).where(Instrument.symbol == sector_symbol))
            sector_bars = _bars(session, sector.id, provider.name) if sector else []
            sector_value, sector_factor = relative_strength(bars, sector_bars)
            sector_score = sector_value if sector_bars else None
            holding_rows = session.execute(
                select(
                    Instrument.sector,
                    PortfolioHolding.quantity,
                    PortfolioHolding.average_cost,
                )
                .join(PortfolioHolding, PortfolioHolding.instrument_id == Instrument.id)
                .where(PortfolioHolding.quantity > 0)
            ).all()
            holdings = [
                (sector_name, quantity * average_cost)
                for sector_name, quantity, average_cost in holding_rows
            ]
            portfolio_score, portfolio_factor = portfolio_suitability(holdings, instrument.sector)
            decision = generate_decision(
                analysis,
                bars[-1].close,
                fundamental_score=fundamental,
                news_score=news,
                market_regime_score=regime,
                sector_strength_score=sector_score,
                portfolio_score=portfolio_score,
            )
            now = datetime.now(UTC)
            technical_complete = all(
                value is not None
                for value in (
                    analysis.sma_20,
                    analysis.sma_50,
                    analysis.rsi_14,
                    analysis.macd_signal,
                    analysis.atr_14,
                )
            )
            completeness = sum(
                (
                    40 if technical_complete else 20,
                    20 if fundamental is not None else 0,
                    10 if news is not None else 0,
                    10 if spy_bars else 0,
                    10 if sector_bars else 0,
                    10,
                )
            )
            context_positive = []
            context_negative = []
            for label, value, factor in (
                ("Market regime", regime, regime_factor),
                ("Sector strength", sector_score, sector_factor),
                ("Portfolio suitability", portfolio_score, portfolio_factor),
            ):
                if value is None:
                    context_negative.append(f"Missing {label.lower()} data")
                elif value >= 55:
                    context_positive.append(factor)
                elif value <= 45:
                    context_negative.append(factor)
            if fundamental is None:
                context_negative.append("Fundamental snapshot is missing or older than 7 days")
            if news is None:
                context_negative.append("News snapshot is missing or older than 2 days")

            signal = Signal(
                instrument_id=instrument.id,
                strategy_name="Quality Momentum Swing",
                strategy_version="1.0",
                recommendation=decision.recommendation,
                technical_score=analysis.score,
                fundamental_score=fundamental,
                news_score=news,
                market_regime_score=regime,
                sector_strength_score=sector_score,
                portfolio_score=portfolio_score,
                confidence_score=decision.confidence_score,
                risk_score=decision.risk_score,
                entry_price=decision.entry_price,
                stop_price=decision.stop_price,
                target_price=decision.target_price,
                holding_period_days=20,
                explanation=decision.explanation,
                positive_factors=analysis.positive_factors + context_positive,
                negative_factors=analysis.negative_factors + context_negative,
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


@router.post("/outcomes/evaluate", response_model=dict)
def evaluate_outcomes(request: Request, horizon_days: int = 20) -> dict:
    evaluated = 0
    with request.app.state.database.session_factory() as session:
        signals = session.scalars(select(Signal).options(selectinload(Signal.instrument))).all()
        for signal in signals:
            existing = session.scalar(
                select(SignalOutcome.id).where(
                    SignalOutcome.signal_id == signal.id,
                    SignalOutcome.horizon_days == horizon_days,
                )
            )
            if existing:
                continue
            prices = session.scalars(
                select(PriceHistory)
                .where(
                    PriceHistory.instrument_id == signal.instrument_id,
                    PriceHistory.timestamp > signal.generated_at,
                )
                .order_by(PriceHistory.timestamp)
                .limit(horizon_days)
            ).all()
            if len(prices) < horizon_days:
                continue
            entry = signal.entry_price
            returns = [(price.close / entry - 1) * 100 for price in prices]
            session.add(
                SignalOutcome(
                    signal_id=signal.id,
                    horizon_days=horizon_days,
                    entry_price=entry,
                    exit_price=prices[-1].close,
                    return_percentage=returns[-1],
                    maximum_favourable_excursion=max(returns),
                    maximum_adverse_excursion=min(returns),
                )
            )
            evaluated += 1
        session.commit()
    return {"evaluated": evaluated, "horizon_days": horizon_days}


@router.get("/outcomes", response_model=list[dict])
def list_outcomes(request: Request) -> list[dict]:
    with request.app.state.database.session_factory() as session:
        rows = session.execute(
            select(SignalOutcome, Signal, Instrument)
            .join(Signal, Signal.id == SignalOutcome.signal_id)
            .join(Instrument, Instrument.id == Signal.instrument_id)
            .order_by(SignalOutcome.evaluated_at.desc())
            .limit(200)
        ).all()
        return [
            {
                "symbol": instrument.symbol,
                "recommendation": signal.recommendation,
                "generated_at": signal.generated_at.isoformat(),
                "horizon_days": outcome.horizon_days,
                "return_percentage": outcome.return_percentage,
                "maximum_favourable_excursion": outcome.maximum_favourable_excursion,
                "maximum_adverse_excursion": outcome.maximum_adverse_excursion,
            }
            for outcome, signal, instrument in rows
        ]


@router.get("/backtest/{symbol}", response_model=dict)
def backtest_signal(
    symbol: str,
    request: Request,
    provider: str = "twelve_data",
    horizon_days: int = Query(default=20, ge=5, le=120),
    position_value: float = Query(default=10_000, gt=0, le=10_000_000),
    commission_per_order: float = Query(default=1.0, ge=0, le=100),
    regulatory_fee_bps: float = Query(default=0.2, ge=0, le=100),
    slippage_bps: float = Query(default=5.0, ge=0, le=500),
) -> dict:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol.upper()))
        if instrument is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
        bars = _bars(session, instrument.id, provider)
        dividend_snapshot = session.scalar(
            select(ResearchSnapshot).where(
                ResearchSnapshot.instrument_id == instrument.id,
                ResearchSnapshot.data_type == "dividends",
            )
        )
        dividends = dividend_snapshot.payload if dividend_snapshot else []
    assumptions = BacktestAssumptions(
        horizon_days=horizon_days,
        position_value=position_value,
        commission_per_order=commission_per_order,
        regulatory_fee_bps=regulatory_fee_bps,
        slippage_bps=slippage_bps,
    )
    try:
        result = run_backtest(bars, assumptions, dividends=dividends)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            str(exc),
        ) from exc
    return {"symbol": instrument.symbol, "provider": provider, **result}
