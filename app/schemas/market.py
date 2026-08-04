from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstrumentCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    asset_type: str = Field(min_length=1, max_length=32)
    sector: str | None = None
    currency: str = "USD"
    country: str = "US"


class InstrumentResponse(InstrumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    instruments: list[InstrumentCreate] = Field(default_factory=list)


class WatchlistResponse(BaseModel):
    id: int
    name: str
    description: str | None
    instruments: list[InstrumentResponse]


class MarketBarResponse(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int | None
    interval: str


class MarketDataResponse(BaseModel):
    symbol: str
    provider: str
    bars: list[MarketBarResponse]


class MarketRefreshRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=25)
    provider: str | None = None
    limit: int = Field(default=100, ge=1, le=5000)


class MarketRefreshResponse(BaseModel):
    provider: str
    symbols_refreshed: int
    bars_stored: int
