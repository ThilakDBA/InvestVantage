import os
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from shared import configure_page, research_notice

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

configure_page("Instrument Research")


@st.cache_data(ttl=30)
def instruments() -> list[dict]:
    response = httpx.get(f"{API_BASE_URL}/api/v1/instruments", timeout=10)
    response.raise_for_status()
    return response.json()


def clear_analysis() -> None:
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("analysis_context", None)


def reset_range_controls() -> None:
    clear_analysis()
    st.session_state.pop("maximum_price_bars", None)
    if st.session_state.get("range_mode") == "Preset windows":
        for key in (
            "manual_interval",
            "manual_timezone",
            "manual_start_date",
            "manual_start_time",
            "manual_end_date",
            "manual_end_time",
        ):
            st.session_state.pop(key, None)


def change_preset_window() -> None:
    clear_analysis()
    st.session_state.pop("maximum_price_bars", None)


try:
    catalogue = instruments()
except httpx.HTTPError as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

if not catalogue:
    st.warning("No instruments are loaded. Run the watchlist seed service.")
    st.stop()

controls, content = st.columns([1, 3])
with controls:
    st.subheader("Analysis controls")
    symbol = st.selectbox("Instrument", [item["symbol"] for item in catalogue])
    selected_instrument = next(item for item in catalogue if item["symbol"] == symbol)
    provider = st.selectbox("Market data", ["mock", "twelve_data", "finnhub"])
    range_mode = st.selectbox(
        "Range selection",
        ["Preset windows", "Custom date & time"],
        key="range_mode",
        on_change=reset_range_controls,
        help="Choose a standard lookback or an exact date and timestamp range.",
    )
    preset_intervals = {
        "1 Hour": (timedelta(hours=1), "1min"),
        "2 Hours": (timedelta(hours=2), "1min"),
        "4 Hours": (timedelta(hours=4), "1min"),
        "8 Hours": (timedelta(hours=8), "5min"),
        "12 Hours": (timedelta(hours=12), "5min"),
        "1 Day": (timedelta(days=1), "5min"),
        "3 Days": (timedelta(days=3), "15min"),
        "7 Days": (timedelta(days=7), "30min"),
        "15 Days": (timedelta(days=15), "1h"),
        "1 Month": (pd.DateOffset(months=1), "1h"),
        "3 Months": (pd.DateOffset(months=3), "4h"),
        "6 Months": (pd.DateOffset(months=6), "1day"),
        "9 Months": (pd.DateOffset(months=9), "1day"),
        "1 Year": (pd.DateOffset(years=1), "1day"),
        "2 Years": (pd.DateOffset(years=2), "1day"),
        "5 Years": (pd.DateOffset(years=5), "1day"),
        "Maximum history": (None, "1day"),
    }
    if range_mode == "Preset windows":
        chart_window = st.selectbox(
            "Lookback window",
            list(preset_intervals),
            index=7,
            key="preset_window",
            on_change=change_preset_window,
        )
        selected_delta, selected_interval = preset_intervals[chart_window]
        manual_start = manual_end = None
        range_is_valid = True
        st.caption(f"Automatic candle interval: `{selected_interval}`")
        recommended_points = {
            "1 Hour": 120,
            "2 Hours": 240,
            "4 Hours": 300,
            "8 Hours": 300,
            "12 Hours": 400,
            "1 Day": 500,
            "3 Days": 500,
            "7 Days": 500,
            "15 Days": 500,
            "1 Month": 750,
            "3 Months": 750,
            "6 Months": 250,
            "9 Months": 300,
            "1 Year": 400,
            "2 Years": 600,
            "5 Years": 1500,
            "Maximum history": 2000,
        }[chart_window]
    else:
        selected_interval = st.selectbox(
            "Candle interval",
            ["1min", "5min", "15min", "30min", "1h", "2h", "4h", "8h", "1day"],
            index=4,
            key="manual_interval",
            on_change=clear_analysis,
        )
        manual_timezone = st.selectbox(
            "Time zone",
            ["America/New_York", "UTC", "Asia/Kolkata"],
            key="manual_timezone",
            on_change=clear_analysis,
        )
        manual_start_date = st.date_input(
            "Start date",
            value=datetime.now().date() - timedelta(days=7),
            key="manual_start_date",
            on_change=clear_analysis,
        )
        manual_start_time = st.time_input(
            "Start time",
            value=datetime.min.time(),
            key="manual_start_time",
            on_change=clear_analysis,
        )
        manual_end_date = st.date_input(
            "End date",
            value=datetime.now().date(),
            key="manual_end_date",
            on_change=clear_analysis,
        )
        manual_end_time = st.time_input(
            "End time",
            value=datetime.now().time().replace(second=0, microsecond=0),
            key="manual_end_time",
            on_change=clear_analysis,
        )
        selected_zone = ZoneInfo(manual_timezone)
        manual_start = datetime.combine(
            manual_start_date, manual_start_time, tzinfo=selected_zone
        ).astimezone(UTC)
        manual_end = datetime.combine(
            manual_end_date, manual_end_time, tzinfo=selected_zone
        ).astimezone(UTC)
        chart_window = "Manual"
        selected_delta = manual_end - manual_start
        range_is_valid = manual_end > manual_start
        if not range_is_valid:
            st.error("End date/time must be after start date/time.")
        recommended_points = 500
    requested_points = st.slider(
        "Maximum price bars",
        35,
        2000,
        recommended_points,
        key="maximum_price_bars",
        help="Higher values provide more history but consume more provider credits and load time.",
    )
    analyse = st.button(
        "Analyse", type="primary", use_container_width=True, disabled=not range_is_valid
    )
    st.info(
        "Mock data is deterministic. Finnhub provides one quote and is not suitable "
        "for indicators yet."
    )

with content:
    context = (
        symbol,
        provider,
        requested_points,
        selected_interval,
        chart_window,
        manual_start,
        manual_end,
    )
    if analyse:
        try:
            analysis_params = {
                "provider": provider,
                "refresh": "true",
                "limit": requested_points,
                "interval": selected_interval,
            }
            if manual_start and manual_end:
                analysis_params["start_at"] = manual_start.isoformat()
                analysis_params["end_at"] = manual_end.isoformat()
            response = httpx.get(
                f"{API_BASE_URL}/api/v1/analysis/{symbol}/technical",
                params=analysis_params,
                timeout=30,
            )
            response.raise_for_status()
            st.session_state["analysis_result"] = response.json()
            st.session_state["analysis_context"] = context
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("detail", "Analysis request failed")
            st.error(detail)
        except httpx.HTTPError as exc:
            st.error(f"API request failed: {exc}")

    result = st.session_state.get("analysis_result")
    if result is None or st.session_state.get("analysis_context") != context:
        st.subheader("Select an instrument and run technical analysis")
        st.write("The dashboard will show trend, momentum, volatility, volume and scoring factors.")
        st.stop()

    score, trend, price, rsi = st.columns(4)
    history = pd.DataFrame(result["price_history"])
    latest_close = history.iloc[-1]["close"]
    score.metric("Technical score", f"{result['technical_score']}/100")
    trend.metric("Trend", result["trend"].title())
    price.metric("Latest close", f"${latest_close:,.2f}")
    rsi_value = result["indicators"]["rsi_14"]
    rsi.metric("RSI (14)", f"{rsi_value:.1f}" if rsi_value is not None else "N/A")

    st.subheader(f"{symbol} {selected_interval} price history")
    history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True)
    history["sma_20"] = history["close"].rolling(20).mean()
    history["sma_50"] = history["close"].rolling(50).mean()
    delta = history["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    history["rsi_14"] = 100 - 100 / (1 + gain / loss.replace(0, float("nan")))
    history["macd"] = (
        history["close"].ewm(span=12, adjust=False).mean()
        - history["close"].ewm(span=26, adjust=False).mean()
    )
    history["macd_signal"] = history["macd"].ewm(span=9, adjust=False).mean()
    latest_timestamp = history["timestamp"].max()
    if range_mode == "Custom date & time":
        chart_data = history[
            (history["timestamp"] >= manual_start) & (history["timestamp"] <= manual_end)
        ]
    elif selected_delta is None:
        chart_data = history
    else:
        chart_data = history[history["timestamp"] >= latest_timestamp - selected_delta]
    if chart_data.empty:
        st.warning("No bars exist inside the selected date/time range.")
        st.stop()
    display_timezone = manual_timezone if range_mode == "Custom date & time" else "America/New_York"
    chart_data = chart_data.copy()
    chart_data["timestamp"] = chart_data["timestamp"].dt.tz_convert(display_timezone)
    chart = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.55, 0.18, 0.14, 0.13],
    )
    chart.add_trace(
        go.Candlestick(
            x=chart_data["timestamp"],
            open=chart_data["open"],
            high=chart_data["high"],
            low=chart_data["low"],
            close=chart_data["close"],
            increasing_line_color="#14b8a6",
            decreasing_line_color="#ef4444",
            name="OHLC",
        ),
        row=1,
        col=1,
    )
    chart.add_trace(
        go.Scatter(x=chart_data["timestamp"], y=chart_data["sma_20"], name="SMA 20"),
        row=1,
        col=1,
    )
    chart.add_trace(
        go.Scatter(x=chart_data["timestamp"], y=chart_data["sma_50"], name="SMA 50"),
        row=1,
        col=1,
    )
    chart.add_trace(
        go.Bar(
            x=chart_data["timestamp"],
            y=chart_data["volume"].fillna(0),
            marker_color="#64748b",
            name="Volume",
        ),
        row=2,
        col=1,
    )
    chart.add_trace(
        go.Scatter(x=chart_data["timestamp"], y=chart_data["rsi_14"], name="RSI 14"),
        row=3,
        col=1,
    )
    chart.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=3, col=1)
    chart.add_hline(y=30, line_dash="dot", line_color="#14b8a6", row=3, col=1)
    chart.add_trace(
        go.Scatter(x=chart_data["timestamp"], y=chart_data["macd"], name="MACD"),
        row=4,
        col=1,
    )
    chart.add_trace(
        go.Scatter(x=chart_data["timestamp"], y=chart_data["macd_signal"], name="MACD signal"),
        row=4,
        col=1,
    )
    chart.update_layout(
        height=780,
        autosize=True,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        hovermode="x",
        hoverdistance=80,
        spikedistance=-1,
        dragmode="zoom",
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "y": 1.02, "x": 0},
        uirevision=f"{symbol}-{provider}-{selected_interval}-{chart_window}",
        transition={"duration": 0},
    )
    chart.update_xaxes(
        range=[chart_data["timestamp"].min(), chart_data["timestamp"].max()],
        showspikes=False,
    )
    chart.update_yaxes(fixedrange=False)
    st.plotly_chart(
        chart,
        use_container_width=True,
        key=f"research-chart-{symbol}-{provider}-{selected_interval}-{chart_window}",
        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": False,
            "doubleClick": "reset",
        },
    )
    st.caption(
        f"{provider} · {selected_interval} OHLCV · {display_timezone} · "
        f"{chart_data['timestamp'].min():%d %b %Y %H:%M} to "
        f"{chart_data['timestamp'].max():%d %b %Y %H:%M} · {len(chart_data)} bars. "
        "Drag to zoom, double-click to reset, and hover for exact values. Mouse-wheel zoom is "
        "disabled to prevent accidental chart collapse."
    )
    research_tab, news_tab, earnings_tab, actions_tab = st.tabs(
        ["Fundamentals", "News", "Earnings", "Corporate actions"]
    )
    research_response = httpx.get(
        f"{API_BASE_URL}/api/v1/research/{symbol}",
        timeout=20,
    )
    research = research_response.json() if research_response.is_success else None
    research_refresh_supported = selected_instrument["asset_type"].upper() == "STOCK"
    if st.button(
        "Refresh fundamentals, news and earnings",
        use_container_width=True,
        disabled=not research_refresh_supported,
    ):
        refresh_response = httpx.get(
            f"{API_BASE_URL}/api/v1/research/{symbol}",
            params={"refresh": "true"},
            timeout=45,
        )
        if refresh_response.is_success:
            st.success("Research data refreshed from Finnhub")
            st.rerun()
        else:
            st.error(refresh_response.json().get("detail", "Research refresh failed"))
    with research_tab:
        if research and research["fundamentals"]["available"]:
            st.metric("Fundamental score", f"{research['fundamentals']['score']}/100")
            metrics = research["fundamentals"]["data"]
            selected = {
                key: metrics.get(key)
                for key in (
                    "peTTM",
                    "roeTTM",
                    "netProfitMarginTTM",
                    "revenueGrowthTTMYoy",
                    "epsGrowthTTMYoy",
                    "52WeekHigh",
                    "52WeekLow",
                )
            }
            st.dataframe(
                pd.DataFrame(selected.items(), columns=["Metric", "Value"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No persisted fundamentals. Run the real-data seed command.")
    with news_tab:
        items = research["news"]["data"] if research and research["news"]["available"] else []
        if items:
            st.metric("Headline score", f"{research['news']['score']}/100")
            for item in items[:10]:
                st.markdown(f"**{item.get('headline', 'Untitled')}**  \n{item.get('source', '')}")
        else:
            st.info("No persisted company news.")
    with earnings_tab:
        events = (
            research["earnings"]["data"] if research and research["earnings"]["available"] else []
        )
        if events:
            st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
        else:
            st.info("No earnings events are available.")
    with actions_tab:
        dividends = (
            research["dividends"]["data"] if research and research["dividends"]["available"] else []
        )
        splits = research["splits"]["data"] if research and research["splits"]["available"] else []
        if dividends:
            st.markdown("**Dividends**")
            st.dataframe(pd.DataFrame(dividends), use_container_width=True, hide_index=True)
        if splits:
            st.markdown("**Stock splits**")
            st.dataframe(pd.DataFrame(splits), use_container_width=True, hide_index=True)
        if not dividends and not splits:
            st.info("Corporate-action data is unavailable on the configured provider plan.")

    positives, negatives = st.columns(2)
    with positives:
        st.subheader("Positive factors")
        for factor in result["positive_factors"] or ["No positive factor confirmed"]:
            st.success(factor)
    with negatives:
        st.subheader("Risk factors")
        for factor in result["negative_factors"] or ["No negative factor confirmed"]:
            st.warning(factor)

    st.subheader("Indicators")
    indicator_table = pd.DataFrame(
        [{"Indicator": key.upper(), "Value": value} for key, value in result["indicators"].items()]
    )
    st.dataframe(indicator_table, use_container_width=True, hide_index=True)

    st.subheader("Quality Momentum signal")
    signal_supported = provider == "twelve_data"
    if provider == "mock":
        st.warning("Mock prices are synthetic. Signal generation is disabled for research use.")
    elif provider == "finnhub":
        st.warning("Finnhub currently supplies one quote, not enough history for a signal.")
    else:
        st.caption(
            "Composite research signal using real daily history plus every available fundamental, "
            "news, market-regime, sector and portfolio component."
        )
    if st.button(
        "Generate research signal",
        use_container_width=True,
        disabled=not signal_supported,
    ):
        signal_response = httpx.post(
            f"{API_BASE_URL}/api/v1/signals/generate",
            json={"symbols": [symbol], "provider": provider, "limit": requested_points},
            timeout=30,
        )
        if signal_response.is_success:
            signal = signal_response.json()[0]
            left, middle, right = st.columns(3)
            left.metric("Recommendation", signal["recommendation"])
            middle.metric("Confidence", f"{signal['confidence_score']}/100")
            right.metric("Risk", f"{signal['risk_score']}/100")
            st.write(signal["explanation"])
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Component": "Technical", "Score": signal["technical_score"]},
                        {"Component": "Fundamentals", "Score": signal["fundamental_score"]},
                        {"Component": "News", "Score": signal["news_score"]},
                        {"Component": "Market regime", "Score": signal["market_regime_score"]},
                        {"Component": "Sector strength", "Score": signal["sector_strength_score"]},
                        {"Component": "Portfolio", "Score": signal["portfolio_score"]},
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.write(
                {
                    "Entry": signal["entry_price"],
                    "Stop reference": signal["stop_price"],
                    "Target reference": signal["target_price"],
                }
            )
        else:
            st.error(signal_response.json().get("detail", "Signal generation failed"))

    st.subheader("Tracked signal outcomes")
    outcome_response = httpx.get(f"{API_BASE_URL}/api/v1/signals/outcomes", timeout=10)
    outcomes = outcome_response.json() if outcome_response.is_success else []
    if outcomes:
        outcome_frame = pd.DataFrame(outcomes)
        st.bar_chart(outcome_frame, x="symbol", y="return_percentage")
        st.dataframe(outcome_frame, use_container_width=True, hide_index=True)
    else:
        st.info("Outcomes appear after enough post-signal trading days have been collected.")

    st.subheader("Backtest laboratory")
    with st.expander("Execution and cost assumptions", expanded=True):
        assumption_left, assumption_middle, assumption_right = st.columns(3)
        with assumption_left:
            backtest_horizon = st.slider("Holding period", 5, 60, 20)
            position_value = st.number_input("Position value ($)", 100.0, 1_000_000.0, 10_000.0)
        with assumption_middle:
            commission = st.number_input("Commission per order ($)", 0.0, 100.0, 1.0)
            regulatory_fee = st.number_input("Regulatory fee (bps)", 0.0, 100.0, 0.2)
        with assumption_right:
            slippage = st.number_input("Slippage per side (bps)", 0.0, 500.0, 5.0)
            st.caption("Broker execution remains disabled. These values affect simulation only.")
    backtest_response = httpx.get(
        f"{API_BASE_URL}/api/v1/signals/backtest/{symbol}",
        params={
            "provider": provider,
            "horizon_days": backtest_horizon,
            "position_value": position_value,
            "commission_per_order": commission,
            "regulatory_fee_bps": regulatory_fee,
            "slippage_bps": slippage,
        },
        timeout=20,
    )
    if backtest_response.is_success:
        backtest = backtest_response.json()
        left, middle, right, drawdown = st.columns(4)
        left.metric("Walk-forward win rate", f"{backtest['win_rate']}%")
        middle.metric("Average net return", f"{backtest['average_net_return']}%")
        right.metric("Total modeled fees", f"${backtest['total_fees']:,.2f}")
        drawdown.metric("Maximum drawdown", f"{backtest['maximum_drawdown']}%")
        if backtest["equity_curve"]:
            equity_frame = pd.DataFrame(backtest["equity_curve"])
            equity_frame["date"] = pd.to_datetime(equity_frame["date"])
            st.line_chart(equity_frame, x="date", y="equity")
        with st.expander("Backtest trades and disclosures"):
            st.dataframe(
                pd.DataFrame(backtest["trades"]), use_container_width=True, hide_index=True
            )
            for disclosure in backtest["bias_disclosures"]:
                st.warning(disclosure)
    elif provider == "twelve_data":
        st.info(backtest_response.json().get("detail", "Backtest is not available"))

    st.subheader("Portfolio suitability")
    with st.expander("Add or update a paper holding"):
        holding_quantity = st.number_input("Quantity", min_value=0.0, value=0.0)
        holding_cost = st.number_input("Average cost", min_value=0.0, value=0.0)
        if st.button("Save paper holding", use_container_width=True):
            holding_response = httpx.put(
                f"{API_BASE_URL}/api/v1/portfolio/holdings",
                json={
                    "symbol": symbol,
                    "quantity": holding_quantity,
                    "average_cost": holding_cost,
                },
                timeout=10,
            )
            if holding_response.is_success:
                st.success("Paper holding saved")
                st.rerun()
            else:
                st.error(holding_response.json().get("detail", "Holding update failed"))
    exposure_response = httpx.get(f"{API_BASE_URL}/api/v1/portfolio/exposure", timeout=10)
    exposure = exposure_response.json() if exposure_response.is_success else {}
    if exposure.get("sector_exposure"):
        exposure_frame = pd.DataFrame(
            exposure["sector_exposure"].items(), columns=["Sector", "Exposure %"]
        )
        st.bar_chart(exposure_frame, x="Sector", y="Exposure %")
        for warning in exposure.get("warnings", []):
            st.warning(warning)
    else:
        st.info("Add paper holdings through the portfolio API to enable exposure guardrails.")

research_notice()
