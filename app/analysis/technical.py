from dataclasses import dataclass
from statistics import fmean

from app.providers.base import MarketBar


@dataclass(frozen=True, slots=True)
class TechnicalAnalysis:
    trend: str
    score: int
    sma_20: float | None
    sma_50: float | None
    ema_12: float | None
    ema_26: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    atr_14: float | None
    volume_ratio_20: float | None
    support_20: float | None
    resistance_20: float | None
    positive_factors: list[str]
    negative_factors: list[str]


def _sma(values: list[float], period: int) -> float | None:
    return fmean(values[-period:]) if len(values) >= period else None


def _ema_series(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    result = [fmean(values[:period])]
    for value in values[period:]:
        result.append((value - result[-1]) * multiplier + result[-1])
    return result


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [current - previous for previous, current in zip(values, values[1:])]
    gains = [max(change, 0) for change in changes[-period:]]
    losses = [max(-change, 0) for change in changes[-period:]]
    average_gain = fmean(gains)
    average_loss = fmean(losses)
    if average_loss == 0:
        return 100.0
    return 100 - (100 / (1 + average_gain / average_loss))


def _atr(bars: list[MarketBar], period: int = 14) -> float | None:
    if len(bars) <= period:
        return None
    ranges = []
    for previous, current in zip(bars, bars[1:]):
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return fmean(ranges[-period:])


def analyse_bars(bars: list[MarketBar]) -> TechnicalAnalysis:
    ordered = sorted(bars, key=lambda bar: bar.timestamp)
    closes = [bar.close for bar in ordered]
    volumes = [bar.volume for bar in ordered if bar.volume is not None]
    if not closes:
        raise ValueError("Technical analysis requires at least one price bar")

    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    ema_12_series = _ema_series(closes, 12)
    ema_26_series = _ema_series(closes, 26)
    ema_12 = ema_12_series[-1] if ema_12_series else None
    ema_26 = ema_26_series[-1] if ema_26_series else None
    macd_series = []
    if len(closes) >= 26:
        for end in range(26, len(closes) + 1):
            fast = _ema_series(closes[:end], 12)[-1]
            slow = _ema_series(closes[:end], 26)[-1]
            macd_series.append(fast - slow)
    macd = macd_series[-1] if macd_series else None
    signal_series = _ema_series(macd_series, 9)
    macd_signal = signal_series[-1] if signal_series else None
    rsi_14 = _rsi(closes)
    atr_14 = _atr(ordered)
    volume_average = fmean(volumes[-20:]) if len(volumes) >= 20 else None
    volume_ratio = (
        volumes[-1] / volume_average if volume_average and volumes else None
    )
    recent = ordered[-20:]
    support = min(bar.low for bar in recent) if len(recent) >= 20 else None
    resistance = max(bar.high for bar in recent) if len(recent) >= 20 else None

    score = 50
    positive: list[str] = []
    negative: list[str] = []
    latest = closes[-1]
    if sma_20 is not None:
        if latest > sma_20:
            score += 12
            positive.append("Price is above its 20-day moving average")
        else:
            score -= 12
            negative.append("Price is below its 20-day moving average")
    if sma_50 is not None and sma_20 is not None:
        if sma_20 > sma_50:
            score += 12
            positive.append("The 20-day average is above the 50-day average")
        else:
            score -= 12
            negative.append("The 20-day average is below the 50-day average")
    if rsi_14 is not None:
        if 50 <= rsi_14 <= 70:
            score += 10
            positive.append("RSI shows positive momentum without being extremely overbought")
        elif rsi_14 > 75:
            score -= 8
            negative.append("RSI indicates an overbought condition")
        elif rsi_14 < 35:
            score -= 8
            negative.append("RSI indicates weak momentum")
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 10
            positive.append("MACD is above its signal line")
        else:
            score -= 10
            negative.append("MACD is below its signal line")
    if volume_ratio is not None:
        if volume_ratio >= 1.1:
            score += 6
            positive.append("Volume is above its 20-day average")
        elif volume_ratio < 0.8:
            score -= 4
            negative.append("Volume is below its 20-day average")
    score = max(0, min(100, score))
    trend = "bullish" if score >= 65 else "bearish" if score < 40 else "neutral"
    return TechnicalAnalysis(
        trend=trend,
        score=score,
        sma_20=sma_20,
        sma_50=sma_50,
        ema_12=ema_12,
        ema_26=ema_26,
        rsi_14=rsi_14,
        macd=macd,
        macd_signal=macd_signal,
        atr_14=atr_14,
        volume_ratio_20=volume_ratio,
        support_20=support,
        resistance_20=resistance,
        positive_factors=positive,
        negative_factors=negative,
    )
