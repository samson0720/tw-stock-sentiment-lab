from pathlib import Path
import argparse
import json
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.scoring import augment_with_explicit_targets, normalize_analysis
from app.config import get_settings
from app.db.database import connect
from app.llm.groq_client import analyze_news
from app.llm.prompts import PROMPT_VERSION, full_news_text


def _pending_news(
    limit: int,
    reanalyze_old_prompts: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    prompt_filter = (
        "a.news_id IS NULL OR a.prompt_version != ? OR a.status IN ('failed', 'fallback')"
        if reanalyze_old_prompts
        else "a.news_id IS NULL"
    )
    filters = [f"({prompt_filter})"]
    params: list[object] = [PROMPT_VERSION] if reanalyze_old_prompts else []
    if start_date:
        filters.append("date(n.published_at) >= date(?)")
        params.append(start_date)
    if end_date:
        filters.append("date(n.published_at) <= date(?)")
        params.append(end_date)
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT n.id, n.title, n.content
            FROM raw_news n
            LEFT JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE {" AND ".join(filters)}
            ORDER BY COALESCE(n.published_at, n.crawled_at) DESC
            LIMIT ?
            """,
            tuple(params),
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
    parser.add_argument("--start-date", default=None, help="Only analyze news published on or after this date.")
    parser.add_argument("--end-date", default=None, help="Only analyze news published on or before this date.")
    args = parser.parse_args()

    settings = get_settings()
    sleep_seconds = settings.llm_request_sleep_seconds if args.sleep is None else args.sleep
    rows = _pending_news(
        args.limit,
        reanalyze_old_prompts=args.reanalyze_old_prompts,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"Pending news: {len(rows)}")

    processed = 0
    for row in rows:
        result = analyze_news(row["title"], row["content"], model=args.model)
        if result.status == "success" and result.data is not None:
            context = f"{row['title']}\n{full_news_text(row['content'])}"
            data = normalize_analysis(result.data, context=context)
            data = augment_with_explicit_targets(data, row["title"], full_news_text(row["content"]))
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
