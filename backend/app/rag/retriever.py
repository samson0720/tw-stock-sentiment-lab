from __future__ import annotations

import numpy as np

from app.db.database import connect


def _pack(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def _unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def upsert_embeddings(rows: list[dict]) -> None:
    """rows: list of {news_id, stock_id, published_at, embedding (np.ndarray)}"""
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO news_embeddings (news_id, stock_id, published_at, embedding)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(news_id) DO UPDATE SET
                stock_id=EXCLUDED.stock_id,
                published_at=EXCLUDED.published_at,
                embedding=EXCLUDED.embedding
            """,
            [
                (r["news_id"], r["stock_id"], r["published_at"], _pack(r["embedding"]))
                for r in rows
            ],
        )


def search(
    query_vec: np.ndarray,
    top_k: int = 5,
    stock_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    filters: list[str] = []
    params: list = []

    if stock_id:
        filters.append("e.stock_id = ?")
        params.append(stock_id)
    if date_from:
        filters.append("e.published_at >= ?")
        params.append(date_from)
    if date_to:
        filters.append("e.published_at <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT e.news_id, e.stock_id, e.published_at, e.embedding,
                   n.title,
                   a.news_type, a.sentiment, a.target, a.confidence
            FROM news_embeddings e
            JOIN raw_news n ON n.id = e.news_id
            LEFT JOIN llm_news_analysis a ON a.news_id = e.news_id AND a.status = 'success'
            {where}
            """,
            params,
        ).fetchall()

    if not rows:
        return []

    matrix = np.stack([_unpack(r["embedding"]) for r in rows])
    scores = matrix @ query_vec  # cosine similarity (both L2-normalised)
    top_idx = np.argsort(scores)[::-1][:top_k]

    return [
        {
            "news_id": rows[i]["news_id"],
            "score": float(scores[i]),
            "title": rows[i]["title"],
            "published_at": rows[i]["published_at"],
            "stock_id": rows[i]["stock_id"],
            "news_type": rows[i]["news_type"],
            "sentiment": rows[i]["sentiment"],
            "target": rows[i]["target"],
        }
        for i in top_idx
    ]
