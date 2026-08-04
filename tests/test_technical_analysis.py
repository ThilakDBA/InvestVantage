from datetime import UTC, datetime, timedelta

from app.analysis import analyse_bars
from app.providers.base import MarketBar


def rising_bars(count: int = 100) -> list[MarketBar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        MarketBar(
            timestamp=start + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            adjusted_close=101 + index,
            volume=1_000_000 + index * 10_000,
        )
        for index in range(count)
    ]


def test_rising_market_produces_explainable_bullish_analysis() -> None:
    result = analyse_bars(rising_bars())
    assert result.trend == "bullish"
    assert result.score >= 65
    assert result.sma_20 == 190.5
    assert result.sma_50 == 175.5
    assert result.rsi_14 == 100
    assert result.atr_14 == 3
    assert result.support_20 == 179
    assert result.resistance_20 == 201
    assert result.positive_factors


def test_short_history_reports_unavailable_long_period_indicators() -> None:
    result = analyse_bars(rising_bars(10))
    assert result.sma_20 is None
    assert result.rsi_14 is None
    assert result.macd is None
    assert result.trend == "neutral"
