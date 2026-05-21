from __future__ import annotations

from datetime import datetime, time

import pandas as pd


MARKET_CLOSE = time(13, 30)


def parse_datetime(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert("Asia/Taipei").tz_localize(None)
    return ts


def align_to_trading_date(published_at: str | None, trading_dates: list[str]) -> str | None:
    if not trading_dates:
        return None

    dates = pd.to_datetime(pd.Series(sorted(trading_dates))).dt.date.tolist()
    ts = parse_datetime(published_at) or pd.Timestamp(datetime.combine(dates[0], time.min))
    candidate = ts.date()
    if ts.time() > MARKET_CLOSE:
        candidate = candidate + pd.Timedelta(days=1)

    for trading_date in dates:
        if trading_date >= candidate:
            return trading_date.isoformat()
    return None


def future_return(price_df: pd.DataFrame, trading_date: str, horizon: int) -> float | None:
    prices = price_df.sort_values("date").reset_index(drop=True)
    matches = prices.index[prices["date"] == trading_date].tolist()
    if not matches:
        return None
    i = matches[0]
    j = i + horizon
    if j >= len(prices):
        return None
    base = float(prices.loc[i, "close"])
    future = float(prices.loc[j, "close"])
    if base == 0:
        return None
    return future / base - 1
