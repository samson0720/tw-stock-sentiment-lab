from __future__ import annotations

import json

import requests

from app.config import get_settings
from app.rag.embedder import embed, is_available as _embedder_available
from app.rag.retriever import keyword_search, search

_SYSTEM = """\
你是台灣股市新聞分析助理。根據提供的新聞摘要回答問題。
必須以 JSON 格式回答，格式如下：
{
  "answer": "根據以下新聞，...",
  "citations": [{"news_id": 123, "title": "...", "published_at": "..."}]
}
規則：
- answer 用繁體中文
- citations 只列出實際支持答案的新聞（最多 5 筆）
- 若提供的新聞資料不足以回答，在 answer 說明並給出 citations: []
- 不可自行捏造未在新聞中出現的數據\
"""


def _call_groq(messages: list[dict]) -> str:
    settings = get_settings()
    resp = requests.post(
        f"{settings.groq_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.groq_model,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": 1000,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        return {"answer": raw, "citations": []}


def ask(
    question: str,
    stock_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    top_k: int = 5,
) -> dict:
    if _embedder_available():
        query_vec = embed([question])[0]
        hits = search(query_vec, top_k=top_k, stock_id=stock_id, date_from=date_from, date_to=date_to)
        retrieval_mode = "semantic"
    else:
        hits = keyword_search(question, top_k=top_k, stock_id=stock_id, date_from=date_from, date_to=date_to)
        retrieval_mode = "keyword"

    if not hits:
        return {"answer": "找不到符合條件的相關新聞資料。", "citations": []}

    context = "\n\n".join(
        f"[{i + 1}] news_id={h['news_id']} 日期:{h['published_at']} 標的:{h['target'] or '—'} 情緒:{h['sentiment'] or '未知'}\n標題:{h['title']}"
        for i, h in enumerate(hits)
    )

    raw = _call_groq([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"問題：{question}\n\n相關新聞：\n{context}"},
    ])

    result = _parse_json(raw)

    hits_by_id = {h["news_id"]: h for h in hits}
    enriched: list[dict] = []
    for c in result.get("citations", []):
        nid = c.get("news_id")
        if nid in hits_by_id:
            h = hits_by_id[nid]
            enriched.append({
                "news_id": nid,
                "title": h["title"],
                "published_at": h["published_at"],
                "sentiment": h["sentiment"],
                "target": h["target"],
                "score": round(h["score"], 4),
            })
    result["citations"] = enriched
    result["retrieval_mode"] = retrieval_mode
    return result
