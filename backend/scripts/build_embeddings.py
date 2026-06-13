"""Embed all news articles and store vectors in news_embeddings table.

Run once (or re-run to update new articles):
    cd backend
    python -u scripts/build_embeddings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import fetch_all
from app.rag.embedder import embed
from app.rag.retriever import upsert_embeddings

BATCH_SIZE = 32


def _date(val: str | None) -> str | None:
    return val[:10] if val else None


def main() -> None:
    rows = fetch_all(
        """
        SELECT n.id,
               n.title,
               n.content,
               n.published_at,
               CASE WHEN a.news_type = 'stock' AND a.target GLOB '[0-9]*' THEN a.target
                    ELSE NULL
               END AS stock_id
        FROM raw_news n
        LEFT JOIN llm_news_analysis a ON a.news_id = n.id AND a.status = 'success'
        WHERE n.id NOT IN (SELECT news_id FROM news_embeddings)
        """
    )
    total = len(rows)
    if total == 0:
        print("All articles already embedded, nothing to do.")
        return
    print(f"Embedding {total} new articles with BAAI/bge-m3...")

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        texts = [f"{r['title']}\n{(r['content'] or '')[:800]}" for r in batch]
        vecs = embed(texts)

        upsert_embeddings([
            {
                "news_id": r["id"],
                "stock_id": r["stock_id"],
                "published_at": _date(r["published_at"]),
                "embedding": vecs[j],
            }
            for j, r in enumerate(batch)
        ])

        done = min(i + BATCH_SIZE, total)
        print(f"  {done}/{total}")

    print("Done.")


if __name__ == "__main__":
    main()
