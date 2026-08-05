import pandas as pd
import streamlit as st
from shared import configure_page, research_notice, safe_get, score_label


def percentage_change(history: list[dict], close: float | None, period: int) -> float | None:
    if close is None or not history:
        return None
    starting_close = history[-min(period, len(history))]["close"]
    if not starting_close:
        return None
    return (close / starting_close - 1) * 100


configure_page("Watchlist", "👀")

provider = st.selectbox("Stored analysis source", ["twelve_data", "mock"], index=0)
watchlists = safe_get("/api/v1/watchlists", default=[])
signals = safe_get("/api/v1/signals", default=[])
latest_signals = {}
for signal in signals:
    latest_signals.setdefault(signal["symbol"], signal)

if not watchlists:
    st.info("No watchlist is configured.")
    research_notice()
    st.stop()

selected = st.selectbox("Watchlist", watchlists, format_func=lambda item: item["name"])
rows = []
for instrument in selected["instruments"]:
    symbol = instrument["symbol"]
    analysis = safe_get(
        f"/api/v1/analysis/{symbol}/technical",
        {"provider": provider, "refresh": "false", "limit": 260, "interval": "1day"},
        {},
    )
    history = analysis.get("price_history", []) if analysis else []
    signal = latest_signals.get(symbol, {})
    latest = history[-1] if history else {}
    close = latest.get("close")

    rows.append(
        {
            "Symbol": symbol,
            "Company": instrument["name"],
            "Sector": instrument.get("sector") or "—",
            "Price": close,
            "1W %": percentage_change(history, close, 6),
            "1M %": percentage_change(history, close, 22),
            "3M %": percentage_change(history, close, 66),
            "Trend": analysis.get("trend", "Missing").title() if analysis else "Missing",
            "Technical": analysis.get("technical_score") if analysis else None,
            "Recommendation": signal.get("recommendation", "—"),
            "Confidence": signal.get("confidence_score"),
            "Risk": signal.get("risk_score"),
            "Status": score_label(signal.get("confidence_score")),
            "Latest timestamp": latest.get("timestamp", "Not available"),
        }
    )

frame = pd.DataFrame(rows)
st.dataframe(
    frame,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Price": st.column_config.NumberColumn(format="$%.2f"),
        "1W %": st.column_config.NumberColumn(format="%.2f%%"),
        "1M %": st.column_config.NumberColumn(format="%.2f%%"),
        "3M %": st.column_config.NumberColumn(format="%.2f%%"),
        "Technical": st.column_config.ProgressColumn(min_value=0, max_value=100),
        "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=100),
        "Risk": st.column_config.ProgressColumn(min_value=0, max_value=100),
    },
)
st.caption("Missing values are displayed explicitly and are never replaced with synthetic scores.")
research_notice()
