ALLOWED_TARGET_TYPES = {"stock", "etf", "index", "industry", "commodity", "macro", "region", "company_foreign", "other"}


def sentiment_score(sentiment: str | None, confidence: float | None) -> float:
    direction = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(sentiment or "", 0.0)
    return direction * max(0.0, min(1.0, float(confidence or 0.0)))


def _normalized_sentiment(value: object) -> str:
    sentiment = str(value or "neutral").lower().strip()
    return sentiment if sentiment in {"positive", "neutral", "negative"} else "neutral"


def _normalized_confidence(value: object) -> float:
    try:
        confidence = float(value or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return max(0.0, min(1.0, confidence))


def _normalized_target_item(data: dict, default_sentiment: str, default_confidence: float) -> dict | None:
    target = str(data.get("target") or "").strip()
    if not target:
        return None
    target_type = str(data.get("target_type") or "other").lower().strip()
    if target_type not in ALLOWED_TARGET_TYPES:
        target_type = "other"
    sentiment = _normalized_sentiment(data.get("sentiment") or default_sentiment)
    confidence = _normalized_confidence(data.get("confidence", default_confidence))
    return {
        "target_type": target_type,
        "target": target,
        "target_name": str(data.get("target_name") or "").strip(),
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": str(data.get("reason") or "")[:40],
    }


def normalize_analysis(data: dict) -> dict:
    news_type = str(data.get("news_type") or "other").lower().strip()
    if news_type == "ignore":
        news_type = "other"
    if news_type not in {"stock", "etf", "market", "industry", "macro", "other"}:
        news_type = "other"
    target_type = str(data.get("target_type") or "other").lower().strip()
    if target_type not in ALLOWED_TARGET_TYPES:
        target_type = "other"
    sentiment = _normalized_sentiment(data.get("sentiment"))
    confidence = _normalized_confidence(data.get("confidence", 0.0))
    target = str(data.get("target") or "").strip() or None
    target_name = str(data.get("target_name") or "").strip()

    targets = []
    raw_targets = data.get("targets")
    if isinstance(raw_targets, list):
        for item in raw_targets:
            if isinstance(item, dict):
                normalized = _normalized_target_item(item, sentiment, confidence)
                if normalized:
                    targets.append(normalized)
    if target and not any(item["target"] == target for item in targets):
        targets.insert(
            0,
            {
                "target_type": target_type,
                "target": target,
                "target_name": target_name,
                "sentiment": sentiment,
                "confidence": confidence,
                "reason": str(data.get("reason") or "")[:40],
            },
        )
    if not target and targets:
        first = targets[0]
        target_type = first["target_type"]
        target = first["target"]
        target_name = first["target_name"]

    if news_type == "other":
        target_type = "other"
        target = None
        target_name = ""
        targets = []
    elif target is None:
        target_type = "other"
    return {
        "news_type": news_type,
        "target_type": target_type,
        "target": target,
        "target_name": target_name,
        "targets": targets,
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": str(data.get("reason") or "")[:40],
        "sentiment_score": sentiment_score(sentiment, confidence),
    }
