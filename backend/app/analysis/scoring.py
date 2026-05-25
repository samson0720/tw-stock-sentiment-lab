import re


ALLOWED_TARGET_TYPES = {"stock", "etf", "index", "industry", "commodity", "macro", "region", "company_foreign", "other"}
MULTI_TARGET_MARKERS = ("這幾檔", "這2檔", "這3檔", "這4檔", "這5檔", "多檔", "族群", "概念股", "買超前十大", "賣超前十大")
STOCK_NAME_CHARS = r"[\u4e00-\u9fffA-Za-z0-9]{2,12}"


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
    if target_type == "stock" and not re.fullmatch(r"\d{4}", target):
        target_type = "company_foreign"
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
    if target_type == "stock" and target and not re.fullmatch(r"\d{4}", target):
        target_type = "company_foreign"

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
    targets = targets[:5]
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


def _append_target(targets: list[dict], stock_id: str, stock_name: str, sentiment: str, confidence: float, reason: str) -> None:
    if any(item["target"] == stock_id for item in targets):
        return
    targets.append(
        {
            "target_type": "stock",
            "target": stock_id,
            "target_name": stock_name,
            "sentiment": sentiment,
            "confidence": confidence,
            "reason": reason[:40],
        }
    )


def _clean_stock_name(value: str) -> str:
    name = value.strip()
    for separator in ("、", "，", ",", "。", "；", ";", "：", ":", "\n", " "):
        if separator in name:
            name = name.split(separator)[-1].strip()
    for marker in ("族群", "概念股"):
        if marker in name:
            name = name.split(marker)[-1].strip()
    for prefix in ("與", "和", "及", "包含", "包括", "指標股", "個股"):
        if name.startswith(prefix):
            name = name[len(prefix) :].strip()
    return name


def extract_explicit_stock_targets(title: str, content: str, limit: int = 5) -> list[dict]:
    text = f"{title}\n{content}"
    if not any(marker in text for marker in MULTI_TARGET_MARKERS):
        return []
    count_match = re.search(r"這([2-5])檔", text)
    if count_match:
        limit = min(limit, int(count_match.group(1)))
    targets: list[dict] = []
    pattern = rf"({STOCK_NAME_CHARS})[（(]\s*(\d{{4}})\s*[）)]"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        stock_name, stock_id = _clean_stock_name(match.group(1)), match.group(2)
        if not stock_name:
            continue
        _append_target(targets, stock_id, stock_name, "neutral", 0.5, "新聞明確列為多標的")
        if len(targets) >= limit:
            return targets
    return targets


def augment_with_explicit_targets(analysis: dict, title: str, content: str) -> dict:
    explicit_targets = extract_explicit_stock_targets(title, content)
    if len(explicit_targets) < 2:
        return analysis

    existing_targets = list(analysis.get("targets") or [])
    merged = []
    for item in existing_targets + explicit_targets:
        if not isinstance(item, dict) or not item.get("target"):
            continue
        if any(existing["target"] == item["target"] for existing in merged):
            continue
        merged.append(item)
        if len(merged) >= 5:
            break
    if len(merged) < 2:
        return analysis

    primary = merged[0]
    if analysis.get("target"):
        for item in merged:
            if item["target"] == analysis["target"] or item.get("target_name") == analysis.get("target_name"):
                primary = item
                break

    analysis["targets"] = merged
    analysis["target_type"] = primary.get("target_type", analysis.get("target_type"))
    analysis["target"] = primary.get("target") or analysis.get("target")
    analysis["target_name"] = primary.get("target_name") or analysis.get("target_name")
    return analysis
