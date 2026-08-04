import asyncio
from typing import Any

import httpx

from app.providers.base import MarketDataError, MarketDataRateLimitError


class ResilientJsonClient:
    """Small async JSON client with bounded retries and sanitized errors."""

    def __init__(self, timeout_seconds: float, max_retries: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def get(
        self,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, params=params, headers=headers)
                if response.status_code == 429:
                    raise MarketDataRateLimitError("Market-data provider rate limit reached")
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise MarketDataError("Market-data provider returned an invalid response")
                return payload
            except MarketDataRateLimitError:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                if attempt >= self.max_retries:
                    raise MarketDataError("Market-data provider request failed") from exc
                await asyncio.sleep(0.25 * (2**attempt))
            except ValueError as exc:
                raise MarketDataError("Market-data provider returned invalid JSON") from exc
        raise MarketDataError("Market-data provider request failed")
