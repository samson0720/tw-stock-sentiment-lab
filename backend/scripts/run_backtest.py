import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backtest.strategies import run_weekly_top_sentiment_strategy
from app.db.database import connect
from app.utils.time import utc_now_iso


def main() -> None:
    with connect() as conn:
        sentiment = pd.read_sql_query("SELECT * FROM daily_sentiment ORDER BY target, trading_date", conn)
        prices = pd.read_sql_query("SELECT * FROM stock_prices ORDER BY stock_id, date", conn)

    equity, metrics = run_weekly_top_sentiment_strategy(sentiment, prices, top_n=5)
    config = {"top_n": 5, "rebalance": "weekly", "signal_column": "sentiment_ma5"}

    if not equity.empty:
        start_date = str(equity["date"].min())
        end_date = str(equity["date"].max())
    else:
        start_date = None
        end_date = None

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO backtest_results
            (strategy_name, config, start_date, end_date, equity_curve, metrics, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "weekly_top_sentiment_equal_weight",
                json.dumps(config, ensure_ascii=False),
                start_date,
                end_date,
                equity.to_json(orient="records", force_ascii=False),
                json.dumps(metrics, ensure_ascii=False),
                utc_now_iso(),
            ),
        )

    out_dir = Path(__file__).resolve().parents[2] / "outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out_dir / "backtest_equity_curve.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([metrics]).to_csv(out_dir / "backtest_metrics.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
