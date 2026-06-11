from pathlib import Path
import argparse
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import connect
from app.llm.prompts import full_news_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="../outputs/tables/human_validation_sample.csv")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--latest-first", action="store_true")
    args = parser.parse_args()

    filters = ["a.status = 'success'"]
    params: list[object] = []
    if args.start_date:
        filters.append("date(n.published_at) >= date(?)")
        params.append(args.start_date)
    if args.end_date:
        filters.append("date(n.published_at) <= date(?)")
        params.append(args.end_date)
    params.append(args.limit)
    order_by = "COALESCE(n.published_at, n.crawled_at) DESC" if args.latest_first else "random()"

    with connect() as conn:
        df = pd.read_sql_query(
            f"""
            SELECT
                n.id AS news_id,
                n.published_at,
                n.title,
                n.content,
                n.url,
                a.news_type AS llm_news_type,
                a.target_type AS llm_target_type,
                a.target AS llm_target,
                a.target_name AS llm_target_name,
                a.targets AS llm_targets,
                a.sentiment AS llm_sentiment,
                a.confidence,
                a.reason,
                a.sentiment_score,
                a.model_name,
                a.prompt_version,
                '' AS human_news_type,
                '' AS human_target_type,
                '' AS human_target,
                '' AS human_sentiment,
                '' AS type_correct,
                '' AS target_correct,
                '' AS sentiment_correct,
                '' AS note
            FROM raw_news n
            JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE {" AND ".join(filters)}
            ORDER BY {order_by}
            LIMIT ?
            """,
            conn,
            params=tuple(params),
        )
    if not df.empty:
        df["cleaned_content"] = df["content"].map(full_news_text)
        df = df.drop(columns=["content"])
        columns = [
            "news_id",
            "published_at",
            "title",
            "cleaned_content",
            "url",
            "llm_news_type",
            "llm_target_type",
            "llm_target",
            "llm_target_name",
            "llm_targets",
            "llm_sentiment",
            "confidence",
            "reason",
            "sentiment_score",
            "model_name",
            "prompt_version",
            "human_news_type",
            "human_target_type",
            "human_target",
            "human_sentiment",
            "type_correct",
            "target_correct",
            "sentiment_correct",
            "note",
        ]
        df = df[columns]
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Exported {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
