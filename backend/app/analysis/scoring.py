def sentiment_score(sentiment: str | None, confidence: float | None) -> float:
    direction = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(sentiment or "", 0.0)
    return direction * max(0.0, min(1.0, float(confidence or 0.0)))


def normalize_analysis(data: dict) -> dict:
    news_type = str(data.get("news_type") or "ignore").lower().strip()
    if news_type not in {"stock", "market", "industry", "ignore"}:
        news_type = "ignore"
    sentiment = str(data.get("sentiment") or "neutral").lower().strip()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = "neutral"
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    target = data.get("target")
    if news_type == "market" and not target:
        target = "0050"
    if news_type == "ignore":
        target = None
    elif target is not None:
        target = str(target).strip() or None
    return {
        "news_type": news_type,
        "target": target,
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": str(data.get("reason") or ""),
        "sentiment_score": sentiment_score(sentiment, confidence),
    }
