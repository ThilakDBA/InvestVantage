from app.analysis.technical import TechnicalAnalysis
from app.strategies import generate_decision


def test_quality_momentum_decision_is_explainable() -> None:
    analysis = TechnicalAnalysis(
        trend="bullish",
        score=82,
        sma_20=110,
        sma_50=100,
        ema_12=112,
        ema_26=105,
        rsi_14=62,
        macd=2,
        macd_signal=1,
        atr_14=3,
        volume_ratio_20=1.2,
        support_20=104,
        resistance_20=120,
        positive_factors=["Positive trend"],
        negative_factors=[],
    )
    decision = generate_decision(analysis, 115)
    assert decision.recommendation == "BUY"
    assert decision.stop_price == 109
    assert decision.target_price == 124
    assert decision.confidence_score >= 80
    assert decision.invalidation_conditions


def test_confidence_penalizes_missing_research_components() -> None:
    analysis = TechnicalAnalysis(
        trend="bullish",
        score=72,
        sma_20=110,
        sma_50=100,
        ema_12=112,
        ema_26=105,
        rsi_14=62,
        macd=2,
        macd_signal=1,
        atr_14=3,
        volume_ratio_20=1.2,
        support_20=104,
        resistance_20=120,
        positive_factors=["Positive trend"],
        negative_factors=[],
    )
    partial = generate_decision(analysis, 115)
    complete = generate_decision(
        analysis,
        115,
        fundamental_score=70,
        news_score=68,
        market_regime_score=74,
        sector_strength_score=69,
        portfolio_score=75,
    )
    assert complete.confidence_score > partial.confidence_score
