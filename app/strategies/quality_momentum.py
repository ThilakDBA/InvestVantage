from dataclasses import dataclass

from app.analysis import TechnicalAnalysis


@dataclass(frozen=True, slots=True)
class SignalDecision:
    recommendation: str
    confidence_score: int
    risk_score: int
    entry_price: float
    stop_price: float | None
    target_price: float | None
    explanation: str
    invalidation_conditions: list[str]


def generate_decision(
    analysis: TechnicalAnalysis,
    latest_price: float,
    *,
    fundamental_score: int | None = None,
    news_score: int | None = None,
    market_regime_score: int | None = None,
    sector_strength_score: int | None = None,
    portfolio_score: int | None = None,
) -> SignalDecision:
    components = [
        (analysis.score, 40),
        (fundamental_score, 20),
        (news_score, 10),
        (market_regime_score, 10),
        (sector_strength_score, 10),
        (portfolio_score, 10),
    ]
    available = [(value, weight) for value, weight in components if value is not None]
    score = round(sum(value * weight for value, weight in available) / sum(w for _, w in available))
    recommendation = (
        "BUY"
        if score >= 75
        else "WATCH"
        if score >= 65
        else "HOLD"
        if score >= 50
        else "REDUCE"
        if score >= 35
        else "AVOID"
    )
    atr = analysis.atr_14
    stop = latest_price - 2 * atr if atr else analysis.support_20
    target = latest_price + 3 * atr if atr else analysis.resistance_20
    volatility_pct = (atr / latest_price * 100) if atr and latest_price else 0
    risk = min(100, round(30 + volatility_pct * 8 + len(analysis.negative_factors) * 8))
    agreement = 100 - round(sum(abs(value - score) for value, _ in available) / len(available))
    indicator_completeness = sum(
        value is not None
        for value in (
            analysis.sma_20,
            analysis.sma_50,
            analysis.rsi_14,
            analysis.macd_signal,
            analysis.atr_14,
        )
    )
    confidence = max(
        0,
        min(100, round(agreement * 0.7 + indicator_completeness / 5 * 30)),
    )
    explanation = (
        f"{recommendation.title()} - composite score {score}/100 from "
        f"{len(available)} available research components, with "
        f"{len(analysis.positive_factors)} positive and "
        f"{len(analysis.negative_factors)} technical factors."
    )
    invalidation = []
    if stop is not None:
        invalidation.append(f"Reassess if price closes below {stop:.2f}")
    invalidation.append("Reassess after material earnings, guidance, or regulatory news")
    return SignalDecision(
        recommendation=recommendation,
        confidence_score=confidence,
        risk_score=risk,
        entry_price=latest_price,
        stop_price=stop,
        target_price=target,
        explanation=explanation,
        invalidation_conditions=invalidation,
    )
