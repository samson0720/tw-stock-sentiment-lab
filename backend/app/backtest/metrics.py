from __future__ import annotations

import math

import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return float(drawdown.min())


def performance_metrics(
    equity_df: pd.DataFrame,
    equity_column: str = "equity",
    return_column: str | None = None,
    number_of_rebalances: int = 0,
) -> dict:
    if equity_df.empty or len(equity_df) < 2:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "number_of_rebalances": number_of_rebalances,
        }

    equity = equity_df[equity_column].astype(float)
    if return_column and return_column in equity_df.columns:
        returns = equity_df[return_column].astype(float).dropna()
    else:
        returns = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    annualized_return = float((1 + total_return) ** (252 / max(len(returns), 1)) - 1)
    annual_volatility = float(returns.std(ddof=0) * math.sqrt(252)) if not returns.empty else 0.0
    sharpe = annualized_return / annual_volatility if annual_volatility else 0.0
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annual_volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown(equity),
        "win_rate": float((returns > 0).mean()) if not returns.empty else 0.0,
        "number_of_rebalances": number_of_rebalances,
    }
