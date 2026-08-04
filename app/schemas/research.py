from datetime import datetime

from pydantic import BaseModel


class ResearchComponent(BaseModel):
    score: int | None
    available: bool
    provider: str
    retrieved_at: datetime | None
    factors: list[str]
    risks: list[str]
    data: dict | list


class ResearchResponse(BaseModel):
    symbol: str
    fundamentals: ResearchComponent
    news: ResearchComponent
    earnings: ResearchComponent
    data_completeness: int
