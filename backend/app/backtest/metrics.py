from __future__ import annotations

import math

import pandas as pd


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return float(drawdown.min())


def performance_metrics(equity_df: pd.DataFrame) -> dict:
    if equity_df.empty or len(equity_df) < 2:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "annual_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "trade_count": 0,
        }

    equity = equity_df["equity"].astype(float)
    returns = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    annual_return = float((1 + total_return) ** (252 / max(len(returns), 1)) - 1)
    annual_volatility = float(returns.std(ddof=0) * math.sqrt(252)) if not returns.empty else 0.0
    sharpe = annual_return / annual_volatility if annual_volatility else 0.0
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown(equity),
        "win_rate": float((returns > 0).mean()) if not returns.empty else 0.0,
        "trade_count": int(len(returns)),
    }
