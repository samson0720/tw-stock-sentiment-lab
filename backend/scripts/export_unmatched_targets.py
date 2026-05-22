from pathlib import Path
import argparse
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.targets import normalize_target
from app.db.database import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="../outputs/tables/unmatched_targets.csv")
    args = parser.parse_args()

    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        price_targets = {
            row["stock_id"]
            for row in conn.execute("SELECT DISTINCT stock_id FROM stock_prices")
        }
        rows = conn.execute(
            """
            SELECT a.news_type, a.target AS original_target, n.title AS example_title
            FROM llm_news_analysis a
            JOIN raw_news n ON n.id = a.news_id
            WHERE a.status = 'success'
              AND a.news_type IN ('stock', 'market', 'industry')
              AND a.target IS NOT NULL
            """
        ).fetchall()

    records: list[dict[str, object]] = []
    for row in rows:
        original_target = row["original_target"]
        normalized_target = normalize_target(row["news_type"], original_target)
        if normalized_target and normalized_target in price_targets:
            continue
        records.append(
            {
                "original_target": original_target,
                "normalized_target": normalized_target or "",
                "news_type": row["news_type"],
                "example_title": row["example_title"],
            }
        )

    if records:
        df = pd.DataFrame(records)
        grouped = (
            df.groupby(["original_target", "normalized_target", "news_type"], dropna=False)
            .agg(count=("example_title", "size"), example_title=("example_title", "first"))
            .reset_index()
            .sort_values(["count", "original_target"], ascending=[False, True])
        )
    else:
        grouped = pd.DataFrame(
            columns=["original_target", "normalized_target", "news_type", "count", "example_title"]
        )
    grouped.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Unmatched target rows: {len(grouped)} -> {output_path}")


if __name__ == "__main__":
    main()
