import json


PROMPT_VERSION = "twstock-news-v1"


def news_excerpt(title: str, content: str, max_chars: int = 1200) -> str:
    paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
    excerpt = "\n".join(paragraphs[:2]) if paragraphs else content
    return excerpt[:max_chars]


def build_news_analysis_messages(title: str, content: str) -> list[dict]:
    schema = {
        "news_type": "stock | market | industry | ignore",
        "target": "stock id/company name, TAIEX/0050, industry name, or null",
        "sentiment": "positive | neutral | negative",
        "confidence": "number from 0 to 1",
        "reason": "one short Traditional Chinese sentence",
    }
    return [
        {
            "role": "system",
            "content": (
                "你是台股新聞分類與情緒分析助理。只輸出一個合法 JSON object，"
                "不要 markdown，不要多餘文字。分類必須保守，無法判斷就用 ignore 或 neutral。"
            ),
        },
        {
            "role": "user",
            "content": (
                "請依照固定 JSON schema 判斷這篇台股新聞的類型、主要標的與情緒。\n"
                f"Schema: {json.dumps(schema, ensure_ascii=False)}\n\n"
                f"新聞標題：{title}\n\n"
                f"新聞摘要：{news_excerpt(title, content)}"
            ),
        },
    ]
