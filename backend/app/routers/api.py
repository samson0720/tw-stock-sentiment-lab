from fastapi import APIRouter, HTTPException, Query

from app.services.news_service import get_news, list_news
from app.services.summary_service import (
    backtest_results,
    daily_brief_history,
    daily_sentiment,
    latest_daily_brief,
    returns_analysis,
    sentiment_summary,
    stock_prices,
    stocks,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/news")
def news(
    limit: int = Query(100, ge=1, le=1000),
    news_type: str | None = None,
    sentiment: str | None = None,
) -> list[dict]:
    return list_news(limit=limit, news_type=news_type, sentiment=sentiment)


@router.get("/news/{news_id}")
def news_detail(news_id: int) -> dict:
    row = get_news(news_id)
    if row is None:
        raise HTTPException(status_code=404, detail="News not found")
    return row


@router.get("/sentiment/summary")
def sentiment_summary_endpoint() -> dict:
    return sentiment_summary()


@router.get("/sentiment/daily")
def daily_sentiment_endpoint(target: str | None = None, limit: int = Query(500, ge=1, le=5000)) -> list[dict]:
    return daily_sentiment(target=target, limit=limit)


@router.get("/stocks")
def stocks_endpoint() -> list[dict]:
    return stocks()


@router.get("/stocks/{stock_id}/prices")
def prices_endpoint(stock_id: str, limit: int = Query(500, ge=1, le=5000)) -> list[dict]:
    return stock_prices(stock_id=stock_id, limit=limit)


@router.get("/analysis/returns")
def returns_endpoint(limit: int = Query(2000, ge=1, le=10000)) -> list[dict]:
    return returns_analysis(limit=limit)


@router.get("/backtest/results")
def backtest_endpoint() -> list[dict]:
    return backtest_results()


@router.get("/daily-brief/latest")
def latest_daily_brief_endpoint() -> dict:
    row = latest_daily_brief()
    if row is None:
        raise HTTPException(status_code=404, detail="Daily brief not found")
    return row


@router.get("/daily-brief/history")
def daily_brief_history_endpoint(limit: int = Query(30, ge=1, le=365)) -> list[dict]:
    return daily_brief_history(limit=limit)
