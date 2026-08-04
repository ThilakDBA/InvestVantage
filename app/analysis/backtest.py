from dataclasses import asdict, dataclass
from datetime import datetime

from app.analysis import analyse_bars
from app.providers.base import MarketBar
from app.strategies import generate_decision


@dataclass(frozen=True, slots=True)
class BacktestAssumptions:
    horizon_days: int = 20
    step_days: int = 5
    position_value: float = 10_000
    commission_per_order: float = 1.0
    regulatory_fee_bps: float = 0.2
    slippage_bps: float = 5.0
    use_adjusted_prices: bool = True
    universe_method: str = "current_watchlist"


def _event_date(event: dict) -> datetime | None:
    for key in ("date", "exDate", "paymentDate"):
        value = event.get(key)
        if value:
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _dividend_cash(events: list[dict], start: datetime, end: datetime) -> float:
    total = 0.0
    for event in events:
        event_date = _event_date(event)
        amount = event.get("amount") or event.get("dividend") or event.get("cashAmount")
        if event_date and start.date() < event_date.date() <= end.date() and amount is not None:
            total += float(amount)
    return total


def run_backtest(
    bars: list[MarketBar],
    assumptions: BacktestAssumptions,
    *,
    dividends: list[dict] | None = None,
) -> dict:
    minimum = 60 + assumptions.horizon_days
    if len(bars) < minimum:
        raise ValueError(f"At least {minimum} bars are required")
    dividends = dividends or []
    trades: list[dict] = []
    equity = assumptions.position_value
    equity_curve = []
    for index in range(60, len(bars) - assumptions.horizon_days, assumptions.step_days):
        window = bars[: index + 1]
        analysis = analyse_bars(window)
        decision = generate_decision(analysis, window[-1].close)
        if decision.recommendation not in {"BUY", "WATCH"}:
            continue
        entry_bar = window[-1]
        exit_bar = bars[index + assumptions.horizon_days]
        entry_reference = (
            entry_bar.adjusted_close
            if assumptions.use_adjusted_prices and entry_bar.adjusted_close
            else entry_bar.close
        )
        exit_reference = (
            exit_bar.adjusted_close
            if assumptions.use_adjusted_prices and exit_bar.adjusted_close
            else exit_bar.close
        )
        entry_price = entry_reference * (1 + assumptions.slippage_bps / 10_000)
        exit_price = exit_reference * (1 - assumptions.slippage_bps / 10_000)
        shares = assumptions.position_value / entry_price
        dividend_cash = _dividend_cash(dividends, entry_bar.timestamp, exit_bar.timestamp) * shares
        gross_profit = (exit_price - entry_price) * shares + dividend_cash
        fees = (
            assumptions.commission_per_order * 2
            + (entry_price + exit_price) * shares * assumptions.regulatory_fee_bps / 10_000
        )
        net_profit = gross_profit - fees
        gross_return = gross_profit / assumptions.position_value * 100
        net_return = net_profit / assumptions.position_value * 100
        equity += net_profit
        equity_curve.append({"date": exit_bar.timestamp.isoformat(), "equity": round(equity, 2)})
        trades.append(
            {
                "entry_date": entry_bar.timestamp.isoformat(),
                "exit_date": exit_bar.timestamp.isoformat(),
                "recommendation": decision.recommendation,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "dividend_cash": round(dividend_cash, 2),
                "fees": round(fees, 2),
                "gross_return_percentage": round(gross_return, 2),
                "net_return_percentage": round(net_return, 2),
            }
        )
    returns = [trade["net_return_percentage"] for trade in trades]
    peaks: list[float] = []
    peak = assumptions.position_value
    drawdowns = []
    for point in equity_curve:
        peak = max(peak, point["equity"])
        peaks.append(peak)
        drawdowns.append((point["equity"] / peak - 1) * 100)
    return {
        "sample_size": len(trades),
        "win_rate": round(sum(value > 0 for value in returns) / len(returns) * 100, 2)
        if returns
        else None,
        "average_net_return": round(sum(returns) / len(returns), 2) if returns else None,
        "total_fees": round(sum(trade["fees"] for trade in trades), 2),
        "maximum_drawdown": round(min(drawdowns), 2) if drawdowns else None,
        "ending_equity": round(equity, 2),
        "assumptions": asdict(assumptions),
        "bias_disclosures": [
            "Universe uses today's configured watchlist and therefore has survivorship bias.",
            (
                "Signals use only information available in each price window, "
                "but fundamentals are excluded."
            ),
            "Corporate-action accuracy depends on adjusted prices and provider dividend coverage.",
            "Equity curve compounds isolated signals and does not model overlapping capital usage.",
        ],
        "trades": trades,
        "equity_curve": equity_curve,
    }
