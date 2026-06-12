from pathlib import Path
import argparse
import json
import re
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.targets import normalize_target
from app.db.database import connect
from app.services.price_service import fetch_finmind_prices, fetch_yahoo_chart_prices, fetch_yfinance_prices


REQUIRED_STOCK_IDS = {"0050", "2330", "2317", "2454", "2303", "3481", "00878"}


def _targets_from_db() -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT news_type, target, targets
            FROM llm_news_analysis
            WHERE status = 'success'
              AND news_type IN ('stock', 'etf', 'market', 'industry')
              AND target IS NOT NULL
            """
        ).fetchall()
    targets = set()
    for row in rows:
        try:
            target_items = json.loads(row["targets"] or "[]")
        except json.JSONDecodeError:
            target_items = []
        if not isinstance(target_items, list) or not target_items:
            target_items = [{"target": row["target"], "target_type": row["news_type"]}]
        for item in target_items:
            if isinstance(item, dict):
                targets.add(
                    normalize_target(
                        str(item.get("target_type") or row["news_type"]),
                        item.get("target") or row["target"],
                        item.get("target_name"),
                    )
                )
    stock_ids = {t for t in targets if t and re.match(r"^\d{4,6}[A-Z]?$", str(t))}
    return sorted(REQUIRED_STOCK_IDS | stock_ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-ids", default="")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--source", choices=["finmind", "yfinance"], default="finmind")
    args = parser.parse_args()

    stock_ids = [s.strip() for s in args.stock_ids.split(",") if s.strip()]
    if stock_ids:
        stock_ids = sorted(set(stock_ids) | REQUIRED_STOCK_IDS)
    else:
        stock_ids = _targets_from_db()
    total = 0
    for stock_id in stock_ids:
        stock_id = str(stock_id).zfill(4) if str(stock_id).isdigit() else str(stock_id)
        try:
            if args.source == "finmind":
                try:
                    df = fetch_finmind_prices(stock_id, args.start_date, args.end_date)
                except Exception as exc:
                    print(f"{stock_id}: FinMind failed, fallback to yfinance: {exc}")
                    df = fetch_yfinance_prices(stock_id, args.start_date, args.end_date)
            else:
                df = fetch_yfinance_prices(stock_id, args.start_date, args.end_date)
            if df.empty and args.source == "finmind":
                df = fetch_yfinance_prices(stock_id, args.start_date, args.end_date)
            if df.empty:
                print(f"{stock_id}: yfinance empty, fallback to Yahoo chart API")
                df = fetch_yahoo_chart_prices(stock_id, args.start_date, args.end_date)
        except Exception as exc:
            print(f"{stock_id}: failed: {exc}")
            continue
        if df.empty:
            print(f"{stock_id}: no data")
            continue
        records = df[["stock_id", "date", "open", "high", "low", "close", "volume", "source"]].itertuples(
            index=False, name=None
        )
        with connect() as conn:
            conn.executemany(
                """
                INSERT INTO stock_prices
                (stock_id, date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_id, date) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                    close=EXCLUDED.close, volume=EXCLUDED.volume, source=EXCLUDED.source
                """,
                list(records),
            )
        total += len(df)
        print(f"{stock_id}: stored {len(df)} price rows")
    print(f"Stored total price rows: {total}")


if __name__ == "__main__":
    main()
