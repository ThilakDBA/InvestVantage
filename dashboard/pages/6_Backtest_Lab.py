import pandas as pd
import plotly.express as px
import streamlit as st
from shared import configure_page, research_notice, safe_get

configure_page("Backtest Lab", "🧪")

instruments = safe_get("/api/v1/instruments", default=[])
if not instruments:
    st.stop()
symbol = st.selectbox("Instrument", [item["symbol"] for item in instruments])
provider = st.selectbox("Stored daily-price source", ["twelve_data", "mock"])

with st.form("backtest_assumptions"):
    first, second, third = st.columns(3)
    with first:
        horizon = st.slider("Holding period (trading days)", 5, 60, 20)
        position_value = st.number_input("Position value ($)", 100.0, 1_000_000.0, 10_000.0)
    with second:
        commission = st.number_input("Commission per order ($)", 0.0, 100.0, 1.0)
        regulatory_fee = st.number_input("Regulatory fee (bps)", 0.0, 100.0, 0.2)
    with third:
        slippage = st.number_input("Slippage per side (bps)", 0.0, 500.0, 5.0)
        st.caption("Simulation only. Broker execution remains disabled.")
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
    result = safe_get(f"/api/v1/signals/backtest/{symbol}", params, {})
    zero_cost = safe_get(
        f"/api/v1/signals/backtest/{symbol}",
        {
            **params,
            "commission_per_order": 0,
            "regulatory_fee_bps": 0,
            "slippage_bps": 0,
        },
        {},
    )
    if result:
        win, average, fees, drawdown, equity = st.columns(5)
        win.metric("Win rate", f"{result['win_rate']}%")
        average.metric("Average net return", f"{result['average_net_return']}%")
        fees.metric("Modeled fees", f"${result['total_fees']:,.2f}")
        drawdown.metric("Maximum drawdown", f"{result['maximum_drawdown']}%")
        equity.metric("Ending equity", f"${result['ending_equity']:,.2f}")

        equity_frame = pd.DataFrame(result["equity_curve"])
        trades = pd.DataFrame(result["trades"])
        if not equity_frame.empty:
            equity_frame["date"] = pd.to_datetime(equity_frame["date"])
            equity_frame["peak"] = equity_frame["equity"].cummax()
            equity_frame["drawdown"] = (equity_frame["equity"] / equity_frame["peak"] - 1) * 100
            curve, drawdown_chart = st.columns(2)
            curve.plotly_chart(
                px.line(equity_frame, x="date", y="equity", title="Equity curve"),
                use_container_width=True,
            )
            drawdown_chart.plotly_chart(
                px.area(equity_frame, x="date", y="drawdown", title="Drawdown (%)"),
                use_container_width=True,
            )
        if not trades.empty:
            distribution, outcomes = st.columns(2)
            distribution.plotly_chart(
                px.histogram(
                    trades,
                    x="net_return_percentage",
                    nbins=20,
                    title="Net return distribution",
                ),
                use_container_width=True,
            )
            outcome_counts = trades.assign(
                Outcome=trades["net_return_percentage"].apply(
                    lambda value: "Winning" if value > 0 else "Losing"
                )
            )["Outcome"].value_counts()
            outcomes.plotly_chart(
                px.pie(values=outcome_counts.values, names=outcome_counts.index, title="Outcomes"),
                use_container_width=True,
            )
            trades["exit_date"] = pd.to_datetime(trades["exit_date"])
            monthly = (
                trades.assign(
                    Year=trades["exit_date"].dt.year,
                    Month=trades["exit_date"].dt.strftime("%b"),
                )
                .pivot_table(
                    index="Year", columns="Month", values="net_return_percentage", aggfunc="mean"
                )
                .reindex(
                    columns=[
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
                )
            )
            st.plotly_chart(
                px.imshow(monthly, text_auto=".2f", aspect="auto", title="Monthly mean return (%)"),
                use_container_width=True,
            )
            st.dataframe(trades, use_container_width=True, hide_index=True)
        if zero_cost:
            st.metric(
                "Execution-cost impact",
                f"{result['ending_equity'] - zero_cost['ending_equity']:+,.2f} USD",
                help="Difference between configured assumptions and a zero-cost simulation.",
            )
        for disclosure in result["bias_disclosures"]:
            st.warning(disclosure)
else:
    st.info("Configure the assumptions and run the simulation. Daily stored bars are required.")

research_notice()
