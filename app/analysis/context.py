from collections import defaultdict

from app.providers.base import MarketBar

SECTOR_BENCHMARKS = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Consumer Cyclical": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Consumer Defensive": "XLP",
}


def period_return(bars: list[MarketBar], periods: int = 63) -> float | None:
    if len(bars) < 2:
        return None
    start = bars[-min(len(bars), periods)].close
    return (bars[-1].close / start - 1) * 100 if start else None


def market_regime(bars: list[MarketBar]) -> tuple[int, str]:
    if len(bars) < 50:
        return 50, "Market benchmark history is incomplete"
    closes = [bar.close for bar in bars]
    sma_50 = sum(closes[-50:]) / 50
    return_3m = period_return(bars, 63) or 0
    distance_from_average = (closes[-1] / sma_50 - 1) * 100
    score = max(10, min(90, round(50 + distance_from_average * 4 + return_3m * 1.2)))
    classification = "Risk-on" if score >= 60 else "Risk-off" if score <= 40 else "Neutral"
    return (
        score,
        f"{classification}: SPY is {distance_from_average:+.1f}% versus its 50-day average "
        f"with {return_3m:+.1f}% 3-month momentum",
    )


def relative_strength(asset: list[MarketBar], benchmark: list[MarketBar]) -> tuple[int, str]:
    asset_return = period_return(asset)
    benchmark_return = period_return(benchmark)
    if asset_return is None or benchmark_return is None:
        return 50, "Sector-relative history is incomplete"
    spread = asset_return - benchmark_return
    score = max(5, min(95, round(50 + spread * 1.5)))
    return score, f"3-month return is {spread:+.1f}% versus the sector benchmark"


def portfolio_suitability(
    holdings: list[str | None] | list[tuple[str | None, float]], candidate_sector: str | None
) -> tuple[int, str]:
    if not holdings:
        return 85, "No current holdings; concentration capacity is available"
    exposure: dict[str, float] = defaultdict(float)
    for holding in holdings:
        if isinstance(holding, tuple):
            sector, value = holding
            exposure[sector or "Unknown"] += max(0, value)
        else:
            exposure[holding or "Unknown"] += 1
    total = sum(exposure.values())
    weight = exposure[candidate_sector or "Unknown"] / total * 100 if total else 0
    score = max(15, min(90, round(90 - weight * 1.5)))
    if weight >= 40:
        return (
            score,
            f"Current {candidate_sector or 'Unknown'} exposure is concentrated at {weight:.0f}%",
        )
    if weight >= 25:
        return score, f"Current {candidate_sector or 'Unknown'} exposure is {weight:.0f}%"
    return score, f"Current {candidate_sector or 'Unknown'} exposure is within the 25% guardrail"
