from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    strategy_name: Mapped[str] = mapped_column(String(128))
    strategy_version: Mapped[str] = mapped_column(String(32))
    recommendation: Mapped[str] = mapped_column(String(16), index=True)
    technical_score: Mapped[int] = mapped_column(Integer)
    confidence_score: Mapped[int] = mapped_column(Integer)
    risk_score: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    holding_period_days: Mapped[int] = mapped_column(Integer, default=20)
    explanation: Mapped[str] = mapped_column(Text)
    positive_factors: Mapped[list[str]] = mapped_column(JSON, default=list)
    negative_factors: Mapped[list[str]] = mapped_column(JSON, default=list)
    invalidation_conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    data_completeness: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    instrument: Mapped["Instrument"] = relationship()  # noqa: F821
