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


def generate_decision(analysis: TechnicalAnalysis, latest_price: float) -> SignalDecision:
    score = analysis.score
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
    completeness = sum(
        value is not None
        for value in (analysis.sma_20, analysis.sma_50, analysis.rsi_14, analysis.macd_signal, atr)
    )
    confidence = max(0, min(100, round(score * 0.7 + completeness / 5 * 30)))
    explanation = (
        f"{recommendation.title()} — technical score {score}/100 with "
        f"{len(analysis.positive_factors)} positive and "
        f"{len(analysis.negative_factors)} negative factors."
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
