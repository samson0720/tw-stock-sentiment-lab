from __future__ import annotations

from datetime import datetime, time

import pandas as pd

from app.analysis.targets import normalize_target
from app.db.database import connect


MARKET_CLOSE = time(13, 30)


def _parse_datetime(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts


def align_to_trading_date(published_at: str | None, trading_dates: list[str]) -> str | None:
    ts = _parse_datetime(published_at)
    if ts is None or not trading_dates:
        return None
    date_str = ts.date().isoformat()
    after_close = ts.time() > MARKET_CLOSE
    candidates = [d for d in trading_dates if d > date_str] if after_close else [d for d in trading_dates if d >= date_str]
    return candidates[0] if candidates else None


def build_aligned_returns() -> int:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT n.id AS news_id, n.published_at, a.news_type, a.target, a.sentiment_score
            FROM raw_news n
            JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE a.status = 'success'
              AND a.news_type IN ('stock', 'market')
              AND a.target IS NOT NULL
            """
        ).fetchall()
        price_rows = conn.execute("SELECT stock_id, date, close FROM stock_prices ORDER BY stock_id, date").fetchall()

    prices = pd.DataFrame([dict(row) for row in price_rows])
    if prices.empty:
        return 0

    by_stock: dict[str, pd.DataFrame] = {
        stock_id: group.sort_values("date").reset_index(drop=True)
        for stock_id, group in prices.groupby("stock_id")
    }

    output: list[tuple] = []
    for row in rows:
        target = normalize_target(row["news_type"], row["target"])
        if not target or target not in by_stock:
            continue
        price_df = by_stock[target]
        dates = price_df["date"].tolist()
        trading_date = align_to_trading_date(row["published_at"], dates)
        if not trading_date:
            continue
        idx_list = price_df.index[price_df["date"] == trading_date].tolist()
        if not idx_list:
            continue
        idx = idx_list[0]
        base_close = float(price_df.loc[idx, "close"])

        def future_return(days: int) -> float | None:
            future_idx = idx + days
            if future_idx >= len(price_df) or base_close == 0:
                return None
            return float(price_df.loc[future_idx, "close"]) / base_close - 1.0

        output.append(
            (
                row["news_id"],
                trading_date,
                target,
                row["news_type"],
                row["sentiment_score"],
                future_return(1),
                future_return(3),
                future_return(5),
            )
        )

    with connect() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO aligned_news_returns
            (news_id, trading_date, target, news_type, sentiment_score,
             future_return_1d, future_return_3d, future_return_5d)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            output,
        )
    return len(output)
