import os
from typing import Any

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

SCORE_WEIGHTS = {
    "Technical": 0.40,
    "Fundamentals": 0.20,
    "News": 0.10,
    "Market regime": 0.10,
    "Sector strength": 0.10,
    "Portfolio suitability": 0.10,
}

INDICATOR_HELP = {
    "RSI (14)": (
        "Measures recent momentum from 0 to 100. Values above 70 can indicate an extended "
        "price; values below 30 can indicate weak or oversold momentum."
    ),
    "MACD": "Compares fast and slow exponential averages to describe trend momentum.",
    "ATR (14)": "Measures typical price movement and is used as a volatility reference.",
    "SMA 20/50": "Compares short and medium-term average prices to classify trend direction.",
}


def configure_page(title: str, icon: str = "📈") -> None:
    st.set_page_config(page_title=f"{title} · InvestVantage", page_icon=icon, layout="wide")
    st.title(title)
    st.caption("InvestVantage · Explainable research and paper-trading decision support")


@st.cache_data(ttl=30)
def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    response = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def safe_get(path: str, params: dict[str, Any] | None = None, default=None):
    try:
        return api_get(path, params)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", "Request failed")
        st.warning(f"{detail} ({path})")
    except httpx.HTTPError as exc:
        st.error(f"API unavailable: {exc}")
    return default


def score_label(score: int | float | None) -> str:
    if score is None:
        return "Missing"
    if score >= 65:
        return "Positive"
    if score >= 45:
        return "Neutral"
    return "Caution"


def freshness_label(timestamp: str | None) -> str:
    return timestamp or "Not available"


def source_caption(provider: str, retrieved_at: str | None = None) -> None:
    st.caption(f"Source: {provider} · Retrieved: {freshness_label(retrieved_at)}")


def research_notice() -> None:
    st.divider()
    st.caption(
        "Research only. Data may be delayed or incomplete. Recommendations are not guaranteed, "
        "and broker execution remains disabled."
    )
