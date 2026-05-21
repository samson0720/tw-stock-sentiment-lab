from pathlib import Path
import argparse
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawlers.yahoo_news import fetch_yahoo_news
from app.crawlers.yahoo_news import fetch_yahoo_historical_news
from app.db.database import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--mode", choices=["latest", "historical"], default="latest")
    parser.add_argument("--start-date", default="2026-03-01")
    parser.add_argument("--end-date", default="2026-05-08")
    parser.add_argument(
        "--search-term",
        action="append",
        default=[],
        help="Yahoo News search term for historical mode. Repeatable.",
    )
    args = parser.parse_args()

    if args.mode == "historical":
        items = fetch_yahoo_historical_news(
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit,
            search_terms=args.search_term or None,
        )
    else:
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
