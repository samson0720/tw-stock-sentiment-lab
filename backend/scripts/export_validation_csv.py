from pathlib import Path
import argparse
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="../outputs/tables/human_validation_sample.csv")
    args = parser.parse_args()

    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                n.id AS news_id,
                n.title,
                n.url,
                a.news_type AS llm_news_type,
                a.target AS llm_target,
                a.sentiment AS llm_sentiment,
                a.confidence,
                a.reason,
                '' AS human_news_type,
                '' AS human_target,
                '' AS human_sentiment,
                '' AS type_correct,
                '' AS sentiment_correct,
                '' AS note
            FROM raw_news n
            JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE a.status = 'success'
            ORDER BY random()
            LIMIT ?
            """,
            conn,
            params=(args.limit,),
        )
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Exported {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
