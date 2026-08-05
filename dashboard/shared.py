import os
from html import escape
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
    st.set_page_config(
        page_title=f"{title} · InvestVantage",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --iv-navy: #071426;
            --iv-panel: #0d2038;
            --iv-border: rgba(148, 163, 184, 0.22);
            --iv-cyan: #22d3ee;
            --iv-blue: #3b82f6;
            --iv-text: #e6edf7;
            --iv-muted: #94a3b8;
        }
        .stApp {
            background:
                radial-gradient(circle at 82% 2%, rgba(37, 99, 235, 0.16), transparent 31rem),
                linear-gradient(145deg, #06101f 0%, #091829 58%, #071321 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #071426 0%, #0a1b30 100%);
            border-right: 1px solid var(--iv-border);
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(15, 36, 61, 0.96), rgba(9, 26, 46, 0.96));
            border: 1px solid var(--iv-border);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
        }
        [data-testid="stMetricLabel"] { color: var(--iv-muted); }
        [data-testid="stMetricValue"] { color: var(--iv-text); }
        div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] {
            border: 1px solid var(--iv-border);
            border-radius: 14px;
            overflow: hidden;
        }
        .iv-brand {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin: 0.2rem 0 1.1rem;
        }
        .iv-logo {
            display: grid;
            place-items: center;
            width: 42px;
            height: 42px;
            border-radius: 12px;
            color: #04111f;
            font-weight: 900;
            letter-spacing: -0.08em;
            background: linear-gradient(135deg, var(--iv-cyan), var(--iv-blue));
            box-shadow: 0 8px 24px rgba(34, 211, 238, 0.22);
        }
        .iv-brand-name { color: var(--iv-text); font-size: 1.3rem; font-weight: 750; }
        .iv-brand-tag { color: var(--iv-muted); font-size: 0.78rem; }
        .iv-page-header {
            padding: 1.25rem 1.4rem;
            margin: 0 0 1.4rem;
            border: 1px solid var(--iv-border);
            border-radius: 16px;
            background: linear-gradient(110deg, rgba(15, 42, 70, 0.96), rgba(10, 27, 48, 0.92));
        }
        .iv-page-kicker {
            color: var(--iv-cyan);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }
        .iv-page-title {
            color: var(--iv-text);
            font-size: 2rem;
            font-weight: 760;
            margin: 0.2rem 0;
        }
        .iv-page-subtitle { color: var(--iv-muted); font-size: 0.95rem; }
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown(
            """
            <div class="iv-brand">
              <div class="iv-logo">IV</div>
              <div>
                <div class="iv-brand-name">InvestVantage</div>
                <div class="iv-brand-tag">MARKET INTELLIGENCE</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("Home.py", label="Home", icon="🏠")
        st.page_link("pages/1_Market_Overview.py", label="Market Overview", icon="🌐")
        st.page_link("pages/2_Watchlist.py", label="Watchlist", icon="👁️")
        st.page_link("pages/3_Instrument_Research.py", label="Instrument Research", icon="📈")
        st.page_link("pages/4_Signals.py", label="Signals", icon="🧭")
        st.page_link(
            "pages/5_Fundamentals_Events.py",
            label="Fundamentals & Events",
            icon="📰",
        )
        st.page_link("pages/6_Backtest_Lab.py", label="Backtest Lab", icon="🧪")
        st.page_link("pages/7_Portfolio_Research.py", label="Portfolio Research", icon="💼")
        st.page_link("pages/8_Data_Health.py", label="Data Health", icon="🩺")
        st.divider()
        st.caption("PAPER RESEARCH MODE · BROKER ORDERS OFF")
    st.markdown(
        f"""
        <div class="iv-page-header">
          <div class="iv-page-kicker">InvestVantage Research Workspace</div>
          <div class="iv-page-title">{escape(title)}</div>
          <div class="iv-page-subtitle">
            Explainable market intelligence with visible evidence, risk and data provenance
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
