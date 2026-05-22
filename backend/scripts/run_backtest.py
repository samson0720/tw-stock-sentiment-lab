import argparse
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from app.backtest.strategies import BacktestConfig, run_high_sentiment_equal_weight_strategy
from app.db.database import connect
from app.utils.time import utc_now_iso


STRATEGY_NAME = "High Sentiment Equal Weight Strategy"


def _write_figures(equity: pd.DataFrame) -> None:
    out_dir = PROJECT_ROOT / "outputs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    if equity.empty:
        return

    plot_df = equity.copy()
    plot_df["date"] = pd.to_datetime(plot_df["date"])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(plot_df["date"], plot_df["strategy_equity"], label="Strategy")
    ax.plot(plot_df["date"], plot_df["benchmark_equity"], label="0050 Benchmark")
    ax.set_title("Backtest Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "backtest_equity_curve.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(plot_df["date"], plot_df["strategy_drawdown"], label="Strategy")
    ax.plot(plot_df["date"], plot_df["benchmark_drawdown"], label="0050 Benchmark")
    ax.set_title("Backtest Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "backtest_drawdown.png", dpi=160)
    plt.close(fig)


def _write_tables(equity: pd.DataFrame, positions: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    out_dir = PROJECT_ROOT / "outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_df = pd.DataFrame(
        [
            {"portfolio": "strategy", **metrics["strategy"]},
            {"portfolio": "benchmark_0050", **metrics["benchmark"]},
        ]
    )
    metrics_df.to_csv(out_dir / "backtest_metrics.csv", index=False, encoding="utf-8-sig")
    equity.to_csv(out_dir / "backtest_equity_curve.csv", index=False, encoding="utf-8-sig")
    positions.to_csv(out_dir / "backtest_positions.csv", index=False, encoding="utf-8-sig")
    return metrics_df


def _write_db(equity: pd.DataFrame, metrics: dict, config: dict) -> None:
    start_date = str(equity["date"].min()) if not equity.empty else None
    end_date = str(equity["date"].max()) if not equity.empty else None
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO backtest_results
            (strategy_name, config, start_date, end_date, equity_curve, metrics, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                STRATEGY_NAME,
                json.dumps(config, ensure_ascii=False),
                start_date,
                end_date,
                equity.to_json(orient="records", force_ascii=False),
                json.dumps(metrics, ensure_ascii=False),
                utc_now_iso(),
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--signal-column", default="sentiment_ma5")
    parser.add_argument("--rebalance-frequency", choices=["W-FRI", "M"], default="W-FRI")
    parser.add_argument("--benchmark", default="0050")
    parser.add_argument("--transaction-cost", type=float, default=0.0)
    parser.add_argument("--signal-lookback-days", type=int, default=20)
    args = parser.parse_args()

    config = BacktestConfig(
        top_n=args.top_n,
        signal_column=args.signal_column,
        rebalance_frequency=args.rebalance_frequency,
        benchmark=args.benchmark,
        transaction_cost=args.transaction_cost,
        signal_lookback_days=args.signal_lookback_days,
    )

    with connect() as conn:
        sentiment = pd.read_sql_query("SELECT * FROM daily_sentiment ORDER BY target, trading_date", conn)
        prices = pd.read_sql_query("SELECT * FROM stock_prices ORDER BY stock_id, date", conn)

    equity, positions, metrics = run_high_sentiment_equal_weight_strategy(sentiment, prices, config)
    config_dict = {
        "top_n": config.top_n,
        "signal_column": config.signal_column,
        "rebalance_frequency": config.rebalance_frequency,
        "benchmark": config.benchmark,
        "transaction_cost": config.transaction_cost,
        "signal_lookback_days": config.signal_lookback_days,
    }

    metrics_df = _write_tables(equity, positions, metrics)
    _write_figures(equity)
    _write_db(equity, metrics, config_dict)

    print(json.dumps({"config": config_dict, "metrics": metrics}, ensure_ascii=False, indent=2))
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
