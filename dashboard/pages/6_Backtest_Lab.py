import pandas as pd
import plotly.express as px
import streamlit as st
from shared import configure_page, research_notice, safe_get

configure_page("Backtest Lab", "🧪")

instruments = safe_get("/api/v1/instruments", default=[])
if not instruments:
    st.stop()

with st.form("backtest_assumptions"):
    first, second, third = st.columns(3)
    with first:
        symbol = st.selectbox("Instrument", [item["symbol"] for item in instruments])
        provider = st.selectbox("Stored daily-price source", ["twelve_data", "mock"])
        horizon = st.slider("Holding period (trading days)", 5, 60, 20)
    with second:
        position_value = st.number_input("Position value ($)", 100.0, 1_000_000.0, 10_000.0)
        commission = st.number_input("Commission per order ($)", 0.0, 100.0, 1.0)
    with third:
        regulatory_fee = st.number_input("Regulatory fee (bps)", 0.0, 100.0, 0.2)
        slippage = st.number_input("Slippage per side (bps)", 0.0, 500.0, 5.0)
    run = st.form_submit_button("Run backtest", type="primary", use_container_width=True)

if run:
    params = {
        "provider": provider,
        "horizon_days": horizon,
        "position_value": position_value,
        "commission_per_order": commission,
        "regulatory_fee_bps": regulatory_fee,
        "slippage_bps": slippage,
    }
    st.session_state["backtest_result"] = safe_get(
        f"/api/v1/signals/backtest/{symbol}", params, {}
    )
    st.session_state["backtest_zero_cost"] = safe_get(
        f"/api/v1/signals/backtest/{symbol}",
        {
            **params,
            "commission_per_order": 0,
            "regulatory_fee_bps": 0,
            "slippage_bps": 0,
        },
        {},
    )
    st.session_state["backtest_label"] = f"{symbol} · {provider} · {horizon} trading days"

result = st.session_state.get("backtest_result")
zero_cost = st.session_state.get("backtest_zero_cost")
if result:
    st.caption(st.session_state.get("backtest_label", "Latest completed simulation"))
    win, average, fees, drawdown, equity = st.columns(5)
    win.metric("Win rate", f"{result['win_rate']}%")
    average.metric("Average net return", f"{result['average_net_return']}%")
    fees.metric("Modeled fees", f"${result['total_fees']:,.2f}")
    drawdown.metric("Maximum drawdown", f"{result['maximum_drawdown']}%")
    equity.metric("Ending equity", f"${result['ending_equity']:,.2f}")

    equity_frame = pd.DataFrame(result["equity_curve"])
    trades = pd.DataFrame(result["trades"])
    performance_tab, risk_tab, trades_tab = st.tabs(
        ["Performance", "Risk & distribution", "Trade detail"]
    )

    with performance_tab:
        if not equity_frame.empty:
            equity_frame["date"] = pd.to_datetime(equity_frame["date"])
            equity_frame = equity_frame.sort_values("date")
            equity_frame["peak"] = equity_frame["equity"].cummax()
            equity_frame["drawdown"] = (
                equity_frame["equity"] / equity_frame["peak"] - 1
            ) * 100
            st.plotly_chart(
                px.line(
                    equity_frame,
                    x="date",
                    y="equity",
                    title="Portfolio equity through simulated exits",
                    markers=True,
                ),
                use_container_width=True,
                key="backtest-equity",
            )
        if zero_cost:
            comparison = pd.DataFrame(
                {
                    "Scenario": ["Configured costs", "Zero execution costs"],
                    "Ending equity": [result["ending_equity"], zero_cost["ending_equity"]],
                }
            )
            st.plotly_chart(
                px.bar(
                    comparison,
                    x="Scenario",
                    y="Ending equity",
                    title="Execution-cost impact on ending equity",
                    text_auto=".2f",
                ),
                use_container_width=True,
                key="backtest-cost-impact",
            )

    with risk_tab:
        if not equity_frame.empty:
            st.plotly_chart(
                px.area(
                    equity_frame,
                    x="date",
                    y="drawdown",
                    title="Drawdown from the running equity peak (%)",
                ),
                use_container_width=True,
                key="backtest-drawdown",
            )
        if not trades.empty:
            st.plotly_chart(
                px.histogram(
                    trades,
                    x="net_return_percentage",
                    nbins=20,
                    title="Distribution of net trade returns (%)",
                ),
                use_container_width=True,
                key="backtest-distribution",
            )
            trades["exit_date"] = pd.to_datetime(trades["exit_date"])
            monthly = (
                trades.assign(
                    Year=trades["exit_date"].dt.year,
                    Month=trades["exit_date"].dt.month,
                )
                .pivot_table(
                    index="Year",
                    columns="Month",
                    values="net_return_percentage",
                    aggfunc="mean",
                )
                .reindex(columns=range(1, 13))
            )
            monthly.columns = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            st.plotly_chart(
                px.imshow(
                    monthly,
                    text_auto=".2f",
                    aspect="auto",
                    title="Average net return by exit month (%)",
                ),
                use_container_width=True,
                key="backtest-monthly",
            )

    with trades_tab:
        if trades.empty:
            st.info("No simulated trades matched the current assumptions.")
        else:
            st.dataframe(
                trades.sort_values("exit_date", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("Bias, quality and execution disclosures"):
        st.caption("Simulation only. Broker execution remains disabled.")
        for disclosure in result["bias_disclosures"]:
            st.warning(disclosure)
else:
    st.info("Configure the assumptions and run the simulation. Daily stored bars are required.")

research_notice()
