def sentiment_score(sentiment: str | None, confidence: float | None) -> float:
    direction = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(sentiment or "", 0.0)
    return direction * max(0.0, min(1.0, float(confidence or 0.0)))


def normalize_analysis(data: dict) -> dict:
    news_type = str(data.get("news_type") or "other").lower().strip()
    if news_type == "ignore":
        news_type = "other"
    if news_type not in {"stock", "etf", "market", "industry", "macro", "other"}:
        news_type = "other"
    target_type = str(data.get("target_type") or "other").lower().strip()
    if target_type not in {"stock", "etf", "index", "industry", "commodity", "macro", "company_foreign", "other"}:
        target_type = "other"
    sentiment = str(data.get("sentiment") or "neutral").lower().strip()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = "neutral"
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    target = str(data.get("target") or "").strip() or None
    target_name = str(data.get("target_name") or "").strip()
    if news_type == "other":
        target_type = "other"
        target = None
        target_name = ""
    elif target is None:
        target_type = "other"
    return {
        "news_type": news_type,
        "target_type": target_type,
        "target": target,
        "target_name": target_name,
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": str(data.get("reason") or "")[:40],
        "sentiment_score": sentiment_score(sentiment, confidence),
    }
