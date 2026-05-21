from __future__ import annotations

from datetime import date
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from app.config import get_settings


def fetch_finmind_prices(stock_id: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    from FinMind.data import DataLoader

    settings = get_settings()
    api = DataLoader()
    if settings.finmind_token:
        api.login_by_token(api_token=settings.finmind_token)
    df = api.taiwan_stock_daily(
        stock_id=stock_id,
        start_date=start_date,
        end_date=end_date or date.today().isoformat(),
    )
    if df.empty:
        return df
    return pd.DataFrame(
        {
            "stock_id": stock_id,
            "date": df["date"].astype(str),
            "open": df["open"],
            "high": df["max"],
            "low": df["min"],
            "close": df["close"],
            "volume": df["Trading_Volume"],
            "source": "FinMind",
        }
    )


def fetch_yfinance_prices(stock_id: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    import yfinance as yf

    symbol = stock_id if "." in stock_id else f"{stock_id}.TW"
    df = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    return pd.DataFrame(
        {
            "stock_id": stock_id.replace(".TW", "").replace(".TWO", ""),
            "date": pd.to_datetime(df["Date"]).dt.date.astype(str),
            "open": df["Open"],
            "high": df["High"],
            "low": df["Low"],
            "close": df["Close"],
            "volume": df["Volume"],
            "source": "yfinance",
        }
    )


def fetch_yahoo_chart_prices(stock_id: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    symbol = stock_id if "." in stock_id else f"{stock_id}.TW"
    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        if end_date
        else datetime.now(timezone.utc) + timedelta(days=1)
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    response = requests.get(
        url,
        params={
            "period1": int(start_dt.timestamp()),
            "period2": int(end_dt.timestamp()),
            "interval": "1d",
            "events": "history",
        },
        headers={"User-Agent": "Mozilla/5.0 twstock-sentiment-research/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(timestamps):
        close = quote.get("close", [None] * len(timestamps))[i]
        if close is None:
            continue
        rows.append(
            {
                "stock_id": stock_id.replace(".TW", "").replace(".TWO", ""),
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                "open": quote.get("open", [None] * len(timestamps))[i],
                "high": quote.get("high", [None] * len(timestamps))[i],
                "low": quote.get("low", [None] * len(timestamps))[i],
                "close": close,
                "volume": quote.get("volume", [None] * len(timestamps))[i],
                "source": "YahooChart",
            }
        )
    return pd.DataFrame(rows)
