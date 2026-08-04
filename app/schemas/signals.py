from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SignalGenerateRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=25)
    provider: str = "mock"
    limit: int = Field(default=100, ge=35, le=5000)


class SignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    strategy_name: str
    strategy_version: str
    recommendation: str
    technical_score: int
    fundamental_score: int | None
    news_score: int | None
    market_regime_score: int | None
    sector_strength_score: int | None
    portfolio_score: int | None
    confidence_score: int
    risk_score: int
    entry_price: float
    stop_price: float | None
    target_price: float | None
    holding_period_days: int
    explanation: str
    positive_factors: list[str]
    negative_factors: list[str]
    invalidation_conditions: list[str]
    data_completeness: int
    status: str
    generated_at: datetime
    expires_at: datetime
