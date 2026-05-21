from pathlib import Path
import argparse
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import connect


TABLES = [
    "raw_news",
    "llm_news_analysis",
    "stock_prices",
    "aligned_news_returns",
    "daily_sentiment",
    "backtest_results",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="../outputs/tables")
    args = parser.parse_args()
    out_dir = (ROOT / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        for table in TABLES:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            path = out_dir / f"{table}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"{table}: {len(df)} rows -> {path}")


if __name__ == "__main__":
    main()
