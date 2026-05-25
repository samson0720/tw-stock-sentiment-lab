from app.db.database import fetch_all, fetch_one


def list_news(limit: int = 100, news_type: str | None = None, sentiment: str | None = None) -> list[dict]:
    query = """
        SELECT
            n.id, n.title, n.content, n.source, n.published_at, n.url, n.crawled_at,
            a.status, a.news_type, a.target_type, a.target, a.target_name, a.targets, a.sentiment, a.confidence, a.reason,
            a.sentiment_score, a.model_name, a.prompt_version, a.error_message
        FROM raw_news n
        LEFT JOIN llm_news_analysis a ON a.news_id = n.id
        WHERE (? IS NULL OR a.news_type = ?)
          AND (? IS NULL OR a.sentiment = ?)
        ORDER BY COALESCE(n.published_at, n.crawled_at) DESC
        LIMIT ?
    """
    return fetch_all(query, (news_type, news_type, sentiment, sentiment, limit))


def get_news(news_id: int) -> dict | None:
    query = """
        SELECT
            n.*, a.status, a.news_type, a.target_type, a.target, a.target_name, a.targets, a.sentiment, a.confidence, a.reason,
            a.sentiment_score, a.model_name, a.prompt_version, a.raw_response, a.error_message
        FROM raw_news n
        LEFT JOIN llm_news_analysis a ON a.news_id = n.id
        WHERE n.id = ?
    """
    return fetch_one(query, (news_id,))
