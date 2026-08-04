from datetime import datetime

from pydantic import BaseModel


class PricePoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int | None
    interval: str


class IndicatorValues(BaseModel):
    sma_20: float | None
    sma_50: float | None
    ema_12: float | None
    ema_26: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    atr_14: float | None
    volume_ratio_20: float | None
    support_20: float | None
    resistance_20: float | None


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    provider: str
    interval: str
    trend: str
    technical_score: int
    data_points: int
    indicators: IndicatorValues
    positive_factors: list[str]
    negative_factors: list[str]
    price_history: list[PricePoint]
