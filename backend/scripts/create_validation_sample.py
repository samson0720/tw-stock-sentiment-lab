import argparse
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=100)
    args = parser.parse_args()

    with connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                n.id AS news_id, n.title, n.url,
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
            ORDER BY RANDOM()
            LIMIT ?
            """,
            conn,
            params=(args.sample_size,),
        )

    out_dir = Path(__file__).resolve().parents[2] / "outputs" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "human_validation_sample.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Created validation sample: {path}")


if __name__ == "__main__":
    main()
