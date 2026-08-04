from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Instrument, Watchlist, WatchlistItem
from app.providers import create_market_data_provider
from app.providers.base import (
    MarketDataConfigurationError,
    MarketDataError,
    MarketDataProvider,
    MarketDataRateLimitError,
)
from app.schemas.market import (
    InstrumentResponse,
    MarketBarResponse,
    MarketDataResponse,
    MarketRefreshRequest,
    MarketRefreshResponse,
    WatchlistCreate,
    WatchlistResponse,
)
from app.services.market_data import fetch_and_store
from app.services.watchlists import upsert_watchlist

router = APIRouter(prefix="/api/v1", tags=["market data"])


def _watchlist_response(watchlist: Watchlist) -> WatchlistResponse:
    return WatchlistResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        instruments=[
            InstrumentResponse.model_validate(item.instrument) for item in watchlist.items
        ],
    )


def _provider_error(exc: MarketDataError) -> HTTPException:
    if isinstance(exc, MarketDataConfigurationError):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, MarketDataRateLimitError):
        return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _create_provider(request: Request, name: str | None) -> MarketDataProvider:
    try:
        return create_market_data_provider(request.app.state.settings, name)
    except MarketDataError as exc:
        raise _provider_error(exc) from exc


@router.get("/instruments", response_model=list[InstrumentResponse])
def list_instruments(request: Request) -> list[Instrument]:
    with request.app.state.database.session_factory() as session:
        return list(session.scalars(select(Instrument).order_by(Instrument.symbol)))


@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
def get_instrument(symbol: str, request: Request) -> Instrument:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(
            select(Instrument).where(Instrument.symbol == symbol.upper())
        )
        if instrument is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
        return instrument


@router.get("/watchlists", response_model=list[WatchlistResponse])
def list_watchlists(request: Request) -> list[WatchlistResponse]:
    with request.app.state.database.session_factory() as session:
        watchlists = session.scalars(
            select(Watchlist)
            .options(selectinload(Watchlist.items).selectinload(WatchlistItem.instrument))
            .order_by(Watchlist.name)
        ).unique()
        return [_watchlist_response(watchlist) for watchlist in watchlists]


@router.post(
    "/watchlists", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED
)
def create_watchlist(payload: WatchlistCreate, request: Request) -> WatchlistResponse:
    with request.app.state.database.session_factory() as session:
        watchlist = upsert_watchlist(session, payload)
        loaded = session.scalar(
            select(Watchlist)
            .where(Watchlist.id == watchlist.id)
            .options(selectinload(Watchlist.items).selectinload(WatchlistItem.instrument))
        )
        if loaded is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Watchlist load failed")
        return _watchlist_response(loaded)


@router.get("/market/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    request: Request,
    provider: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=5000),
) -> MarketDataResponse:
    with request.app.state.database.session_factory() as session:
        instrument = session.scalar(
            select(Instrument).where(Instrument.symbol == symbol.upper())
        )
        if instrument is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Instrument not found")
        market_provider = _create_provider(request, provider)
        try:
            bars, _ = await fetch_and_store(session, market_provider, instrument, limit)
        except MarketDataError as exc:
            raise _provider_error(exc) from exc
        return MarketDataResponse(
            symbol=instrument.symbol,
            provider=market_provider.name,
            bars=[MarketBarResponse(**asdict(bar)) for bar in bars],
        )


@router.post("/market/refresh", response_model=MarketRefreshResponse)
async def refresh_market_data(
    payload: MarketRefreshRequest, request: Request
) -> MarketRefreshResponse:
    market_provider = _create_provider(request, payload.provider)
    bars_stored = 0
    refreshed = 0
    with request.app.state.database.session_factory() as session:
        for symbol in dict.fromkeys(item.upper() for item in payload.symbols):
            instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol))
            if instrument is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Instrument not found: {symbol}")
            try:
                _, stored = await fetch_and_store(
                    session, market_provider, instrument, payload.limit
                )
            except MarketDataError as exc:
                raise _provider_error(exc) from exc
            bars_stored += stored
            refreshed += 1
    return MarketRefreshResponse(
        provider=market_provider.name,
        symbols_refreshed=refreshed,
        bars_stored=bars_stored,
    )
