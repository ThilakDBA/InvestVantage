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
    if closes[-1] > sma_50 and return_3m > 0:
        return 75, "Risk-on: SPY is above its 50-day average with positive 3-month momentum"
    if closes[-1] < sma_50 and return_3m < 0:
        return 25, "Risk-off: SPY is below its 50-day average with negative 3-month momentum"
    return 50, "Mixed market regime"


def relative_strength(asset: list[MarketBar], benchmark: list[MarketBar]) -> tuple[int, str]:
    asset_return = period_return(asset)
    benchmark_return = period_return(benchmark)
    if asset_return is None or benchmark_return is None:
        return 50, "Sector-relative history is incomplete"
    spread = asset_return - benchmark_return
    score = max(0, min(100, round(50 + spread * 2)))
    return score, f"3-month return is {spread:+.1f}% versus the sector benchmark"


def portfolio_suitability(
    sectors: list[str | None], candidate_sector: str | None
) -> tuple[int, str]:
    if not sectors:
        return 75, "No current holdings; concentration limit is available"
    counts: dict[str, int] = defaultdict(int)
    for sector in sectors:
        counts[sector or "Unknown"] += 1
    weight = counts[candidate_sector or "Unknown"] / len(sectors) * 100
    if weight >= 40:
        return (
            25,
            f"Current {candidate_sector or 'Unknown'} exposure is concentrated at {weight:.0f}%",
        )
    if weight >= 25:
        return 50, f"Current {candidate_sector or 'Unknown'} exposure is {weight:.0f}%"
    return 80, f"Current {candidate_sector or 'Unknown'} exposure is within the 25% guardrail"
