from pathlib import Path
import argparse
import json
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.scoring import normalize_analysis
from app.config import get_settings
from app.db.database import connect
from app.llm.groq_client import analyze_news
from app.llm.prompts import PROMPT_VERSION


def _pending_news(limit: int, reanalyze_old_prompts: bool = False) -> list[dict]:
    prompt_filter = (
        "a.news_id IS NULL OR a.prompt_version != ? OR a.status = 'failed'"
        if reanalyze_old_prompts
        else "a.news_id IS NULL"
    )
    params: tuple[object, ...] = (PROMPT_VERSION, limit) if reanalyze_old_prompts else (limit,)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT n.id, n.title, n.content
            FROM raw_news n
            LEFT JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE {prompt_filter}
            ORDER BY COALESCE(n.published_at, n.crawled_at) DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--model", default=None)
    parser.add_argument("--sleep", type=float, default=None)
    parser.add_argument(
        "--reanalyze-old-prompts",
        action="store_true",
        help="Re-run rows analyzed with an older prompt_version as well as pending rows.",
    )
    args = parser.parse_args()

    settings = get_settings()
    sleep_seconds = settings.llm_request_sleep_seconds if args.sleep is None else args.sleep
    rows = _pending_news(args.limit, reanalyze_old_prompts=args.reanalyze_old_prompts)
    print(f"Pending news: {len(rows)}")

    processed = 0
    for row in rows:
        result = analyze_news(row["title"], row["content"], model=args.model)
        if result.status == "success" and result.data is not None:
            data = normalize_analysis(result.data)
            values = (
                row["id"],
                "success",
                data["news_type"],
                data["target_type"],
                data["target"],
                data["target_name"],
                json.dumps(data["targets"], ensure_ascii=False),
                data["sentiment"],
                data["confidence"],
                data["reason"],
                data["sentiment_score"],
                result.model_name,
                result.prompt_version,
                result.raw_response,
                result.error_message,
            )
        else:
            values = (
                row["id"],
                "failed",
                None,
                None,
                None,
                None,
                "[]",
                None,
                None,
                "",
                None,
                result.model_name,
                result.prompt_version,
                result.raw_response,
                result.error_message,
            )
        with connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_news_analysis
                (news_id, status, news_type, target_type, target, target_name, targets, sentiment, confidence, reason,
                 sentiment_score, model_name, prompt_version, raw_response, error_message, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                values,
            )
        processed += 1
        print(f"[{processed}/{len(rows)}] news_id={row['id']} status={result.status}")
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
