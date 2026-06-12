from __future__ import annotations

import pandas as pd

from app.analysis.targets import normalize_target
from app.db.database import connect


def build_daily_sentiment() -> int:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.target, r.trading_date, a.sentiment, a.confidence, a.sentiment_score, a.news_type
            FROM aligned_news_returns r
            JOIN llm_news_analysis a ON a.news_id = r.news_id
            WHERE a.status = 'success'
            """
        ).fetchall()
    df = pd.DataFrame([dict(row) for row in rows])
    if df.empty:
        return 0
    df["target"] = df.apply(lambda r: normalize_target(r["news_type"], r["target"]), axis=1)
    df = df.dropna(subset=["target"])

    grouped = df.groupby(["target", "trading_date"], as_index=False).agg(
        news_count=("sentiment_score", "size"),
        sentiment_avg=("sentiment_score", "mean"),
        sentiment_sum=("sentiment_score", "sum"),
        positive_count=("sentiment", lambda s: int((s == "positive").sum())),
        neutral_count=("sentiment", lambda s: int((s == "neutral").sum())),
        negative_count=("sentiment", lambda s: int((s == "negative").sum())),
        avg_confidence=("confidence", "mean"),
    )
    grouped["positive_ratio"] = grouped["positive_count"] / grouped["news_count"]
    grouped["negative_ratio"] = grouped["negative_count"] / grouped["news_count"]
    grouped = grouped.sort_values(["target", "trading_date"])
    for window in (3, 5, 20):
        grouped[f"sentiment_ma{window}"] = grouped.groupby("target")["sentiment_avg"].transform(
            lambda s: s.rolling(window=window, min_periods=1).mean()
        )

    records = grouped[
        [
            "target",
            "trading_date",
            "news_count",
            "sentiment_avg",
            "sentiment_sum",
            "positive_count",
            "neutral_count",
            "negative_count",
            "positive_ratio",
            "negative_ratio",
            "avg_confidence",
            "sentiment_ma3",
            "sentiment_ma5",
            "sentiment_ma20",
        ]
    ].itertuples(index=False, name=None)
    with connect() as conn:
        conn.execute("DELETE FROM daily_sentiment")
        conn.executemany(
            """
            INSERT INTO daily_sentiment
            (target, trading_date, news_count, sentiment_avg, sentiment_sum,
             positive_count, neutral_count, negative_count, positive_ratio,
             negative_ratio, avg_confidence, sentiment_ma3, sentiment_ma5, sentiment_ma20)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(records),
        )
    return len(grouped)
