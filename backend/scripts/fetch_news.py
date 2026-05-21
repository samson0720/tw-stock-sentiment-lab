from pathlib import Path
import argparse
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawlers.yahoo_news import fetch_yahoo_news
from app.db.database import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    items = fetch_yahoo_news(limit=args.limit)
    with connect() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO raw_news
            (title, content, source, published_at, url, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (item.title, item.content, item.source, item.published_at, item.url, item.crawled_at)
                for item in items
            ],
        )
        inserted = conn.total_changes
    print(f"Fetched {len(items)} articles, inserted {inserted} new rows.")


if __name__ == "__main__":
    main()
