from pathlib import Path
import argparse
import csv
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawlers.yahoo_news import clean_text, parse_any_datetime
from app.db.database import connect


REQUIRED_COLUMNS = {"title", "content", "published_at", "url", "source"}


def _valid_row(row: dict[str, str]) -> tuple[str, str, str, str, str] | None:
    title = clean_text(row.get("title", ""))
    content = clean_text(row.get("content", ""))
    published_at = parse_any_datetime(row.get("published_at"))
    url = clean_text(row.get("url", ""))
    source = clean_text(row.get("source", "")) or "Manual Import"
    if not title or not content or not published_at or not url:
        return None
    return title, content, source, published_at, url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    args = parser.parse_args()

    path = Path(args.csv_path)
    if not path.exists():
        raise SystemExit(f"CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise SystemExit(f"Missing columns: {', '.join(sorted(missing))}")
        rows = [_valid_row(row) for row in reader]

    valid_rows = [row for row in rows if row is not None]
    crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO raw_news
            (title, content, source, published_at, url, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO NOTHING
            """,
            [(*row, crawled_at) for row in valid_rows],
        )
    print(f"Read {len(rows)} rows, valid {len(valid_rows)} imported (duplicates by URL skipped).")


if __name__ == "__main__":
    main()
