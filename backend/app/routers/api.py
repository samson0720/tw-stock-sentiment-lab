from fastapi import APIRouter, HTTPException, Query

from app.rag.embedder import is_available as _embedder_available
from app.rag.qa import ask as rag_ask
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


@router.get("/rag/query")
def rag_query(
    q: str = Query(..., description="問題"),
    stock: str | None = Query(None, description="股票代號，如 2330"),
    date_from: str | None = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="結束日期 YYYY-MM-DD"),
    top_k: int = Query(5, ge=1, le=20),
) -> dict:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q cannot be empty")
    if not _embedder_available():
        raise HTTPException(status_code=503, detail="Embedding model not available on this deployment")
    return rag_ask(question=q, stock_id=stock, date_from=date_from, date_to=date_to, top_k=top_k)
