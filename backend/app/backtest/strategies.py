from __future__ import annotations

import pandas as pd

from app.backtest.metrics import performance_metrics


def run_weekly_top_sentiment_strategy(
    daily_sentiment: pd.DataFrame,
    stock_prices: pd.DataFrame,
    top_n: int = 5,
    signal_column: str = "sentiment_ma5",
) -> tuple[pd.DataFrame, dict]:
    if daily_sentiment.empty or stock_prices.empty:
        empty = pd.DataFrame(columns=["date", "equity", "daily_return"])
        return empty, performance_metrics(empty)

    signals = daily_sentiment.copy()
    signals["trading_date"] = pd.to_datetime(signals["trading_date"])
    signals["rebalance_date"] = signals["trading_date"].dt.to_period("W-FRI").dt.end_time.dt.date.astype(str)
    picks = (
        signals.sort_values(["rebalance_date", signal_column], ascending=[True, False])
        .groupby("rebalance_date")
        .head(top_n)
        .groupby("rebalance_date")["target"]
        .apply(list)
        .to_dict()
    )

    prices = stock_prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices.sort_values(["stock_id", "date"])
    prices["daily_return"] = prices.groupby("stock_id")["close"].pct_change().fillna(0)

    rows = []
    current_equity = 1.0
    selected: list[str] = []
    for current_date, day_prices in prices.groupby(prices["date"].dt.date.astype(str)):
        if current_date in picks:
            selected = picks[current_date]
        if selected:
            ret = day_prices.loc[day_prices["stock_id"].isin(selected), "daily_return"].mean()
            daily_return = float(ret) if pd.notna(ret) else 0.0
        else:
            daily_return = 0.0
        current_equity *= 1 + daily_return
        rows.append({"date": current_date, "equity": current_equity, "daily_return": daily_return})

    equity = pd.DataFrame(rows)
    return equity, performance_metrics(equity)
