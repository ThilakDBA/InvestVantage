from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.analysis import router as analysis_router
from app.api.health import router as health_router
from app.api.market import router as market_router
from app.api.signals import router as signals_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.base import Base
from app.database.models import (  # noqa: F401
    Instrument,
    PriceHistory,
    Signal,
    Watchlist,
    WatchlistItem,
)
from app.database.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    database = Database(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app_settings.database_url.startswith("sqlite"):
            Path("data").mkdir(exist_ok=True)
            Base.metadata.create_all(database.engine)
        app.state.settings = app_settings
        app.state.database = database
        yield
        database.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="Investment research and paper-trading decision support.",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(market_router)
    application.include_router(analysis_router)
    application.include_router(signals_router)
    return application


app = create_app()
