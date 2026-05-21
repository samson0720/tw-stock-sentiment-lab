from __future__ import annotations

from datetime import date

import pandas as pd


def normalize_finmind_prices(df: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["stock_id", "date", "open", "high", "low", "close", "volume", "source"])
    out = df.rename(
        columns={
            "Trading_Volume": "volume",
            "open": "open",
            "max": "high",
            "min": "low",
            "close": "close",
            "date": "date",
        }
    )
    out["stock_id"] = stock_id
    out["source"] = "FinMind"
    return out[["stock_id", "date", "open", "high", "low", "close", "volume", "source"]]


def fetch_finmind_prices(stock_id: str, start_date: str, end_date: str | None = None, token: str | None = None) -> pd.DataFrame:
    from FinMind.data import DataLoader

    api = DataLoader()
    if token:
        api.login_by_token(api_token=token)
    df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date or date.today().isoformat())
    return normalize_finmind_prices(df, stock_id)


def fetch_yfinance_prices(stock_id: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    import yfinance as yf

    ticker = stock_id if "." in stock_id else f"{stock_id}.TW"
    df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame(columns=["stock_id", "date", "open", "high", "low", "close", "volume", "source"])
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    out = pd.DataFrame(
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
    return out
