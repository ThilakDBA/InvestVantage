from datetime import UTC, datetime, timedelta

import pytest

from app.analysis.context import market_regime, portfolio_suitability, relative_strength
from app.providers.base import MarketBar, MarketDataError
from app.providers.finnhub_research import fundamental_score, news_score
from app.services.market_data import validate_bars


def bars(start: float, daily_gain: float, count: int = 70) -> list[MarketBar]:
    now = datetime.now(UTC) - timedelta(days=count)
    return [
        MarketBar(
            timestamp=now + timedelta(days=index),
            open=start + daily_gain * index,
            high=start + daily_gain * index + 1,
            low=start + daily_gain * index - 1,
            close=start + daily_gain * index + 0.5,
            volume=1000,
        )
        for index in range(count)
    ]


def test_real_price_validation_rejects_bad_ohlc() -> None:
    values = bars(100, 1)
    values[-1] = MarketBar(values[-1].timestamp, 100, 90, 95, 101)
    with pytest.raises(MarketDataError, match="invalid OHLC"):
        validate_bars(values, "twelve_data")


def test_research_context_scores_are_explainable() -> None:
    score, positives, negatives = fundamental_score(
        {
            "roeTTM": 20,
            "netProfitMarginTTM": 15,
            "revenueGrowthTTMYoy": 8,
            "epsGrowthTTMYoy": 10,
            "peTTM": 25,
        }
    )
    assert score > 50
    assert positives
    assert not negatives
    headline_score, factors, _ = news_score([{"headline": "Company beats estimates"}])
    assert headline_score > 50
    assert factors


def test_market_sector_and_portfolio_context() -> None:
    rising = bars(100, 1)
    slower = bars(100, 0.2)
    regime_score, regime_text = market_regime(rising)
    sector_score, sector_text = relative_strength(rising, slower)
    portfolio_score, portfolio_text = portfolio_suitability(
        ["Technology", "Technology", "Technology", "Healthcare"], "Technology"
    )
    assert regime_score > 50 and "Risk-on" in regime_text
    assert sector_score > 50 and "versus" in sector_text
    assert portfolio_score < 50 and "concentrated" in portfolio_text


def test_context_scores_vary_with_magnitude_and_invested_exposure() -> None:
    strong_regime, _ = market_regime(bars(100, 1.0))
    mild_regime, _ = market_regime(bars(100, 0.2))
    assert strong_regime > mild_regime > 50

    concentrated, _ = portfolio_suitability(
        [("Technology", 90_000), ("Healthcare", 10_000)], "Technology"
    )
    diversified, _ = portfolio_suitability(
        [("Technology", 20_000), ("Healthcare", 80_000)], "Technology"
    )
    assert concentrated < diversified


def test_research_scores_respond_to_strength_and_news_volume() -> None:
    moderate, _, _ = fundamental_score(
        {
            "roeTTM": 12,
            "netProfitMarginTTM": 7,
            "revenueGrowthTTMYoy": 2,
            "epsGrowthTTMYoy": 2,
            "peTTM": 30,
        }
    )
    strong, _, _ = fundamental_score(
        {
            "roeTTM": 30,
            "netProfitMarginTTM": 25,
            "revenueGrowthTTMYoy": 20,
            "epsGrowthTTMYoy": 25,
            "peTTM": 20,
        }
    )
    assert strong > moderate

    one_cue, _, _ = news_score([{"headline": "Company reports growth"}])
    several_cues, _, _ = news_score(
        [{"headline": "Company reports record growth and profit beat"} for _ in range(3)]
    )
    assert several_cues > one_cue > 50
