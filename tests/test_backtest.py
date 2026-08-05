from datetime import UTC, datetime, timedelta

from app.analysis.backtest import BacktestAssumptions, run_backtest
from app.providers.base import MarketBar


def rising_bars(count: int = 140) -> list[MarketBar]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    return [
        MarketBar(
            timestamp=start + timedelta(days=index),
            open=100 + index * 0.5,
            high=101 + index * 0.5,
            low=99 + index * 0.5,
            close=100.5 + index * 0.5,
            adjusted_close=100.5 + index * 0.5,
            volume=1_000_000,
        )
        for index in range(count)
    ]


def test_backtest_deducts_execution_costs_and_reports_bias() -> None:
    result = run_backtest(
        rising_bars(),
        BacktestAssumptions(
            horizon_days=20,
            commission_per_order=2,
            regulatory_fee_bps=1,
            slippage_bps=10,
        ),
    )
    assert result["sample_size"] > 0
    assert result["total_fees"] > 0
    assert (
        result["trades"][0]["net_return_percentage"]
        < result["trades"][0]["gross_return_percentage"]
    )
    assert any("survivorship bias" in item for item in result["bias_disclosures"])


def test_backtest_includes_dividend_cash() -> None:
    result = run_backtest(
        rising_bars(),
        BacktestAssumptions(horizon_days=20),
        dividends=[{"exDate": "2025-03-10", "amount": 0.25}],
    )
    assert any(trade["dividend_cash"] > 0 for trade in result["trades"])
