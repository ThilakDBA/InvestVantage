from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.database.models import Instrument, PriceHistory, ResearchSnapshot

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    database: Literal["ok"]
    trading_mode: Literal["paper"]


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    with request.app.state.database.session_factory() as session:
        session.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database="ok",
        trading_mode="paper",
    )


@router.get("/api/v1/system/data-health", response_model=dict)
def data_health(request: Request) -> dict:
    settings = request.app.state.settings
    with request.app.state.database.session_factory() as session:
        active_instruments = session.scalar(
            select(func.count()).select_from(Instrument).where(Instrument.is_active.is_(True))
        )
        price_rows = session.execute(
            select(
                PriceHistory.data_source,
                PriceHistory.interval,
                func.count(PriceHistory.id),
                func.max(PriceHistory.timestamp),
                func.max(PriceHistory.retrieved_at),
            )
            .group_by(PriceHistory.data_source, PriceHistory.interval)
            .order_by(PriceHistory.data_source, PriceHistory.interval)
        ).all()
        research_rows = session.execute(
            select(
                ResearchSnapshot.data_type,
                ResearchSnapshot.provider,
                func.count(ResearchSnapshot.id),
                func.max(ResearchSnapshot.retrieved_at),
            )
            .group_by(ResearchSnapshot.data_type, ResearchSnapshot.provider)
            .order_by(ResearchSnapshot.data_type)
        ).all()
    return {
        "providers": [
            {
                "name": "mock",
                "configured": True,
                "classification": "synthetic",
            },
            {
                "name": "twelve_data",
                "configured": bool(settings.twelve_data_api_key),
                "classification": "external_market_data",
            },
            {
                "name": "finnhub",
                "configured": bool(settings.finnhub_api_key),
                "classification": "external_research_data",
            },
        ],
        "active_instruments": active_instruments or 0,
        "price_inventory": [
            {
                "provider": provider,
                "interval": interval,
                "bar_count": count,
                "latest_market_timestamp": latest_timestamp,
                "last_retrieved_at": retrieved_at,
            }
            for provider, interval, count, latest_timestamp, retrieved_at in price_rows
        ],
        "research_inventory": [
            {
                "data_type": data_type,
                "provider": provider,
                "instrument_count": count,
                "last_retrieved_at": retrieved_at,
            }
            for data_type, provider, count, retrieved_at in research_rows
        ],
        "broker_orders_enabled": False,
    }
