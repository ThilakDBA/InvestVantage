from datetime import UTC, date, datetime, timedelta
from math import exp

from app.providers.base import MarketDataConfigurationError, MarketDataError
from app.providers.http import ResilientJsonClient


class FinnhubResearchProvider:
    base_url = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str | None, client: ResilientJsonClient) -> None:
        self.api_key = api_key
        self.client = client

    async def _get(self, path: str, params: dict) -> dict | list:
        if not self.api_key:
            raise MarketDataConfigurationError("Finnhub API key is not configured")
        payload = await self.client.get(
            f"{self.base_url}/{path}",
            params={**params, "token": self.api_key},
        )
        if isinstance(payload, dict) and payload.get("error"):
            raise MarketDataError(str(payload["error"]))
        return payload

    async def fundamentals(self, symbol: str) -> dict:
        payload = await self._get("stock/metric", {"symbol": symbol, "metric": "all"})
        metrics = payload.get("metric", {}) if isinstance(payload, dict) else {}
        if not metrics:
            raise MarketDataError("Finnhub returned no fundamental metrics")
        return metrics

    async def news(self, symbol: str, days: int = 30) -> list[dict]:
        today = date.today()
        payload = await self._get(
            "company-news",
            {"symbol": symbol, "from": str(today - timedelta(days=days)), "to": str(today)},
        )
        return list(payload)[:50] if isinstance(payload, list) else []

    async def earnings(self, symbol: str) -> list[dict]:
        payload = await self._get("calendar/earnings", {"symbol": symbol})
        return list(payload.get("earningsCalendar", [])) if isinstance(payload, dict) else []

    async def dividends(self, symbol: str) -> list[dict]:
        payload = await self._get("stock/dividend2", {"symbol": symbol})
        return list(payload.get("data", [])) if isinstance(payload, dict) else []

    async def splits(self, symbol: str, years: int = 10) -> list[dict]:
        today = date.today()
        payload = await self._get(
            "stock/split",
            {
                "symbol": symbol,
                "from": str(today - timedelta(days=365 * years)),
                "to": str(today),
            },
        )
        return list(payload) if isinstance(payload, list) else []


def fundamental_score(metrics: dict) -> tuple[int, list[str], list[str]]:
    positives: list[str] = []
    negatives: list[str] = []
    score = 50
    checks = [
        ("roeTTM", 10, 0.6, 12, "Positive return on equity", "Weak return on equity"),
        ("netProfitMarginTTM", 5, 0.5, 10, "Healthy profit margin", "Thin profit margin"),
        ("revenueGrowthTTMYoy", 0, 0.5, 10, "Revenue is growing", "Revenue growth is negative"),
        ("epsGrowthTTMYoy", 0, 0.4, 10, "EPS is growing", "EPS growth is negative"),
    ]
    for key, threshold, scale, cap, positive, negative in checks:
        value = metrics.get(key)
        if not isinstance(value, (int, float)):
            continue
        contribution = max(-cap, min(cap, round((value - threshold) * scale)))
        score += contribution
        if value > threshold:
            positives.append(f"{positive} ({value:.1f})")
        else:
            negatives.append(f"{negative} ({value:.1f})")
    pe = metrics.get("peTTM")
    if isinstance(pe, (int, float)) and pe > 0:
        if 10 <= pe <= 25:
            score += 8
            positives.append(f"P/E valuation is within the preferred range ({pe:.1f})")
        elif pe <= 35:
            score += 3
            positives.append(f"P/E valuation is within the outer guardrail ({pe:.1f})")
        else:
            penalty = min(15, round((pe - 35) * 0.4 + 5))
            score -= penalty
            negatives.append(f"P/E valuation is elevated ({pe:.1f})")
    return max(0, min(100, score)), positives, negatives


def news_score(items: list[dict]) -> tuple[int, list[str], list[str]]:
    positive_words = {"beat", "growth", "upgrade", "record", "raises", "profit"}
    negative_words = {"miss", "downgrade", "lawsuit", "cuts", "loss", "investigation"}
    positive = negative = 0.0
    now = datetime.now(UTC)
    for item in items:
        text = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
        published = source_timestamp(item)
        age_days = max(0, (now - published).days) if published else 30
        recency_weight = exp(-age_days / 14)
        positive += sum(word in text for word in positive_words) * recency_weight
        negative += sum(word in text for word in negative_words) * recency_weight
    total = positive + negative
    score = 50 if total == 0 else round(50 + (positive - negative) / (total + 3) * 40)
    factors = [f"{positive:.1f} recency-weighted positive cues across {len(items)} articles"]
    risks = [f"{negative:.1f} recency-weighted negative cues require review"] if negative else []
    return max(0, min(100, score)), factors, risks


def source_timestamp(item: dict) -> datetime | None:
    value = item.get("datetime")
    return datetime.fromtimestamp(value, UTC) if isinstance(value, (int, float)) else None
