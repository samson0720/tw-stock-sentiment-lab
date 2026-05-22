from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from app.backtest.metrics import max_drawdown, performance_metrics


@dataclass(frozen=True)
class BacktestConfig:
    top_n: int = 5
    signal_column: str = "sentiment_ma5"
    rebalance_frequency: str = "W-FRI"
    benchmark: str = "0050"
    transaction_cost: float = 0.0
    signal_lookback_days: int = 20


def _rebalance_dates(trading_dates: pd.Series, frequency: str) -> set[pd.Timestamp]:
    dates = pd.Series(pd.to_datetime(trading_dates).sort_values().unique())
    if dates.empty:
        return set()
    periods = dates.dt.to_period(frequency)
    return set(dates.groupby(periods).max())


def _select_positions(
    signals: pd.DataFrame,
    available_targets: set[str],
    rebalance_date: pd.Timestamp,
    config: BacktestConfig,
) -> pd.DataFrame:
    start_date = rebalance_date - timedelta(days=config.signal_lookback_days)
    window = signals[
        (signals["trading_date"] <= rebalance_date)
        & (signals["trading_date"] >= start_date)
        & (signals["target"].isin(available_targets))
    ].copy()
    if window.empty:
        return pd.DataFrame(columns=["target", "signal_value", "rank"])

    window = window.sort_values(["target", "trading_date"])
    latest = window.groupby("target", as_index=False).tail(1)
    latest = latest.dropna(subset=["signal_value"]).sort_values(["signal_value", "target"], ascending=[False, True])
    selected = latest.head(config.top_n).copy()
    if selected.empty:
        return pd.DataFrame(columns=["target", "signal_value", "rank"])
    selected["rank"] = range(1, len(selected) + 1)
    return selected[["target", "signal_value", "rank"]]


def run_high_sentiment_equal_weight_strategy(
    daily_sentiment: pd.DataFrame,
    stock_prices: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    config = config or BacktestConfig()
    if daily_sentiment.empty or stock_prices.empty:
        equity = pd.DataFrame(
            columns=[
                "date",
                "strategy_equity",
                "benchmark_equity",
                "strategy_daily_return",
                "benchmark_daily_return",
                "strategy_drawdown",
                "benchmark_drawdown",
            ]
        )
        metrics = {
            "strategy": performance_metrics(equity, "strategy_equity", "strategy_daily_return"),
            "benchmark": performance_metrics(equity, "benchmark_equity", "benchmark_daily_return"),
        }
        return equity, pd.DataFrame(), metrics

    signals = daily_sentiment.copy()
    signals["trading_date"] = pd.to_datetime(signals["trading_date"])
    if config.signal_column not in signals.columns:
        raise ValueError(f"signal column not found: {config.signal_column}")
    signals["signal_value"] = signals[config.signal_column].fillna(signals["sentiment_avg"])

    prices = stock_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices.sort_values(["stock_id", "date"])
    prices["daily_return"] = prices.groupby("stock_id")["close"].pct_change().fillna(0.0)
    returns = prices.pivot_table(index="date", columns="stock_id", values="daily_return", aggfunc="last").sort_index()
    closes = prices.pivot_table(index="date", columns="stock_id", values="close", aggfunc="last").sort_index()

    if config.benchmark not in returns.columns:
        raise ValueError(f"benchmark price data not found: {config.benchmark}")

    signal_start = signals["trading_date"].min()
    trading_dates = pd.Series([date for date in returns.index if date >= signal_start])
    if trading_dates.empty:
        raise ValueError("no trading dates overlap with daily sentiment signals")

    available_targets = set(returns.columns) - {config.benchmark}
    rebalance_dates = _rebalance_dates(trading_dates, config.rebalance_frequency)
    positions_rows: list[dict[str, object]] = []
    equity_rows: list[dict[str, object]] = []

    current_weights: dict[str, float] = {}
    pending_cost = 0.0
    strategy_equity = 1.0
    benchmark_equity = 1.0
    number_of_rebalances = 0

    date_list = list(trading_dates)
    for idx, current_date in enumerate(date_list):
        day_returns = returns.loc[current_date]
        strategy_return = 0.0
        if current_weights:
            strategy_return = sum(
                weight * float(day_returns.get(target, 0.0) or 0.0)
                for target, weight in current_weights.items()
            )
        if pending_cost:
            strategy_return -= pending_cost
            pending_cost = 0.0

        benchmark_return = float(day_returns.get(config.benchmark, 0.0) or 0.0)
        strategy_equity *= 1 + strategy_return
        benchmark_equity *= 1 + benchmark_return

        equity_rows.append(
            {
                "date": current_date.date().isoformat(),
                "strategy_equity": strategy_equity,
                "benchmark_equity": benchmark_equity,
                "strategy_daily_return": strategy_return,
                "benchmark_daily_return": benchmark_return,
            }
        )

        if current_date in rebalance_dates and idx + 1 < len(date_list):
            selected = _select_positions(signals, available_targets, current_date, config)
            if selected.empty:
                continue
            new_weight = 1.0 / len(selected)
            new_weights = {row["target"]: new_weight for _, row in selected.iterrows()}
            all_targets = set(current_weights) | set(new_weights)
            turnover = sum(abs(new_weights.get(target, 0.0) - current_weights.get(target, 0.0)) for target in all_targets)
            pending_cost = config.transaction_cost * turnover
            current_weights = new_weights
            number_of_rebalances += 1
            effective_date = date_list[idx + 1].date().isoformat()
            for _, row in selected.iterrows():
                target = str(row["target"])
                positions_rows.append(
                    {
                        "rebalance_date": current_date.date().isoformat(),
                        "effective_date": effective_date,
                        "target": target,
                        "weight": new_weight,
                        "signal_value": float(row["signal_value"]),
                        "rank": int(row["rank"]),
                        "close_on_rebalance": float(closes.loc[current_date, target])
                        if target in closes.columns and pd.notna(closes.loc[current_date, target])
                        else None,
                    }
                )

    equity = pd.DataFrame(equity_rows)
    positions = pd.DataFrame(positions_rows)
    if not equity.empty:
        equity["strategy_drawdown"] = equity["strategy_equity"] / equity["strategy_equity"].cummax() - 1
        equity["benchmark_drawdown"] = equity["benchmark_equity"] / equity["benchmark_equity"].cummax() - 1

    metrics = {
        "strategy": performance_metrics(
            equity,
            equity_column="strategy_equity",
            return_column="strategy_daily_return",
            number_of_rebalances=number_of_rebalances,
        ),
        "benchmark": performance_metrics(
            equity,
            equity_column="benchmark_equity",
            return_column="benchmark_daily_return",
            number_of_rebalances=0,
        ),
    }
    metrics["strategy"]["max_drawdown"] = max_drawdown(equity["strategy_equity"]) if not equity.empty else 0.0
    metrics["benchmark"]["max_drawdown"] = max_drawdown(equity["benchmark_equity"]) if not equity.empty else 0.0
    return equity, positions, metrics


def run_weekly_top_sentiment_strategy(
    daily_sentiment: pd.DataFrame,
    stock_prices: pd.DataFrame,
    top_n: int = 5,
    signal_column: str = "sentiment_ma5",
) -> tuple[pd.DataFrame, dict]:
    equity, _, metrics = run_high_sentiment_equal_weight_strategy(
        daily_sentiment,
        stock_prices,
        BacktestConfig(top_n=top_n, signal_column=signal_column, rebalance_frequency="W-FRI"),
    )
    legacy = equity.rename(
        columns={"strategy_equity": "equity", "strategy_daily_return": "daily_return"}
    )[["date", "equity", "daily_return"]]
    return legacy, metrics["strategy"]
