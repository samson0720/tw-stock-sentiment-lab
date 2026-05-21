from app.db.database import fetch_all, fetch_one


def sentiment_summary() -> dict:
    totals = fetch_one("SELECT COUNT(*) AS news_count FROM raw_news") or {"news_count": 0}
    analyzed = fetch_one("SELECT COUNT(*) AS analyzed_count FROM llm_news_analysis") or {"analyzed_count": 0}
    failed = fetch_one("SELECT COUNT(*) AS failed_count FROM llm_news_analysis WHERE status = 'failed'") or {
        "failed_count": 0
    }
    by_sentiment = fetch_all(
        "SELECT sentiment, COUNT(*) AS count FROM llm_news_analysis GROUP BY sentiment ORDER BY sentiment"
    )
    by_type = fetch_all(
        "SELECT news_type, COUNT(*) AS count FROM llm_news_analysis GROUP BY news_type ORDER BY news_type"
    )
    return {
        "news_count": totals["news_count"],
        "analyzed_count": analyzed["analyzed_count"],
        "failed_count": failed["failed_count"],
        "by_sentiment": by_sentiment,
        "by_type": by_type,
    }


def daily_sentiment(target: str | None = None, limit: int = 500) -> list[dict]:
    query = """
        SELECT *
        FROM daily_sentiment
        WHERE (? IS NULL OR target = ?)
        ORDER BY trading_date DESC, target
        LIMIT ?
    """
    return fetch_all(query, (target, target, limit))


def returns_analysis(limit: int = 500) -> list[dict]:
    query = """
        SELECT r.*, a.sentiment, a.confidence
        FROM aligned_news_returns r
        JOIN llm_news_analysis a ON a.news_id = r.news_id
        ORDER BY r.trading_date DESC
        LIMIT ?
    """
    return fetch_all(query, (limit,))


def stocks() -> list[dict]:
    return fetch_all(
        """
        SELECT stock_id, MIN(date) AS start_date, MAX(date) AS end_date, COUNT(*) AS rows
        FROM stock_prices
        GROUP BY stock_id
        ORDER BY stock_id
        """
    )


def stock_prices(stock_id: str, limit: int = 500) -> list[dict]:
    return fetch_all(
        "SELECT * FROM stock_prices WHERE stock_id = ? ORDER BY date DESC LIMIT ?",
        (stock_id, limit),
    )


def backtest_results() -> list[dict]:
    return fetch_all(
        """
        SELECT id, strategy_name, config, start_date, end_date, metrics, created_at
        FROM backtest_results
        ORDER BY created_at DESC
        """
    )
