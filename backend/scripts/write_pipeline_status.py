from pathlib import Path
import sys
from datetime import date


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from app.db.database import connect


def _count(conn, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _scalar(conn, query: str, default: int = 0) -> int:
    value = conn.execute(query).fetchone()[0]
    return int(value or default)


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{numerator / denominator * 100:.1f}%"


def _append_distribution(lines: list[str], title: str, rows, value_column: str = "value") -> None:
    lines.extend(["", f"## {title}", "", "| Value | Rows |", "|---|---:|"])
    if not rows:
        lines.append("| None | 0 |")
        return
    for row in rows:
        lines.append(f"| {row[value_column]} | {row['rows']:,} |")


def main() -> None:
    out_path = PROJECT_ROOT / "outputs" / "reports" / "pipeline_status.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        raw_news = _count(conn, "raw_news")
        llm_total = _count(conn, "llm_news_analysis")
        stock_prices = _count(conn, "stock_prices")
        aligned = _count(conn, "aligned_news_returns")
        daily = _count(conn, "daily_sentiment")
        human_validation = _count(conn, "human_validation")
        backtests = _count(conn, "backtest_results")
        success = _scalar(conn, "SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'success'")
        failed = _scalar(conn, "SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'failed'")
        pending = _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM raw_news n
            LEFT JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE a.news_id IS NULL
            """,
        )
        historical_valid = _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM raw_news
            WHERE date(published_at) BETWEEN '2026-03-01' AND '2026-05-08'
              AND title <> ''
              AND content <> ''
              AND published_at IS NOT NULL
            """,
        )
        null_stats = {
            "future_return_1d": _scalar(
                conn, "SELECT COUNT(*) FROM aligned_news_returns WHERE future_return_1d IS NOT NULL"
            ),
            "future_return_3d": _scalar(
                conn, "SELECT COUNT(*) FROM aligned_news_returns WHERE future_return_3d IS NOT NULL"
            ),
            "future_return_5d": _scalar(
                conn, "SELECT COUNT(*) FROM aligned_news_returns WHERE future_return_5d IS NOT NULL"
            ),
        }
        news_type_dist = conn.execute(
            """
            SELECT COALESCE(news_type, 'NULL') AS value, COUNT(*) AS rows
            FROM llm_news_analysis
            GROUP BY news_type
            ORDER BY rows DESC, value
            """
        ).fetchall()
        sentiment_dist = conn.execute(
            """
            SELECT COALESCE(sentiment, 'NULL') AS value, COUNT(*) AS rows
            FROM llm_news_analysis
            GROUP BY sentiment
            ORDER BY rows DESC, value
            """
        ).fetchall()
        target_dist = conn.execute(
            """
            SELECT news_type || ' / ' || COALESCE(target, 'NULL') AS value, COUNT(*) AS rows
            FROM llm_news_analysis
            WHERE status = 'success'
            GROUP BY news_type, target
            ORDER BY rows DESC, value
            LIMIT 40
            """
        ).fetchall()
        price_ranges = conn.execute(
            """
            SELECT stock_id, MIN(date) AS start_date, MAX(date) AS end_date, COUNT(*) AS rows
            FROM stock_prices
            GROUP BY stock_id
            ORDER BY stock_id
            """
        ).fetchall()
        daily_ranges = conn.execute(
            """
            SELECT target, MIN(trading_date) AS start_date, MAX(trading_date) AS end_date,
                   COUNT(*) AS rows, SUM(news_count) AS news_count
            FROM daily_sentiment
            GROUP BY target
            ORDER BY target
            """
        ).fetchall()

    enough_returns = aligned >= 100 and null_stats["future_return_5d"] >= 100
    enough_news = historical_valid >= 300
    ready = enough_news and enough_returns

    lines = [
        "# Pipeline Status",
        "",
        f"Generated at: {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        "Historical data refresh focused on making future returns non-null for downstream notebooks and backtests.",
        "FastAPI and frontend do not call Groq; LLM analysis remains limited to `backend/scripts/analyze_news_with_llm.py`.",
        "",
        "## Table Counts",
        "",
        "| Table | Rows |",
        "|---|---:|",
        f"| raw_news | {raw_news:,} |",
        f"| llm_news_analysis total | {llm_total:,} |",
        f"| llm_news_analysis success | {success:,} |",
        f"| llm_news_analysis failed | {failed:,} |",
        f"| llm_news_analysis pending | {pending:,} |",
        f"| stock_prices | {stock_prices:,} |",
        f"| aligned_news_returns | {aligned:,} |",
        f"| daily_sentiment | {daily:,} |",
        f"| human_validation | {human_validation:,} |",
        f"| backtest_results | {backtests:,} |",
        "",
        "## Historical News Target",
        "",
        "| Requirement | Current | Status |",
        "|---|---:|---|",
        f"| Valid news from 2026-03-01 to 2026-05-08 | {historical_valid:,} | {'OK' if enough_news else 'Needs more data'} |",
    ]
    _append_distribution(lines, "LLM News Type Distribution", news_type_dist)
    _append_distribution(lines, "LLM Sentiment Distribution", sentiment_dist)
    _append_distribution(lines, "LLM Target Distribution Top 40", target_dist)

    lines.extend(
        [
            "",
            "## Future Return Coverage",
            "",
            "| Field | Non-null Rows | Non-null Ratio |",
            "|---|---:|---:|",
        ]
    )
    for field, count in null_stats.items():
        lines.append(f"| {field} | {count:,} | {_pct(count, aligned)} |")

    lines.extend(
        [
            "",
            "## Price Data",
            "",
            "| stock_id | Start Date | End Date | Rows |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in price_ranges:
        lines.append(f"| {row['stock_id']} | {row['start_date']} | {row['end_date']} | {row['rows']:,} |")

    lines.extend(
        [
            "",
            "## Daily Sentiment",
            "",
            "| Target | Start Date | End Date | Rows | News Count |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in daily_ranges:
        lines.append(
            f"| {row['target']} | {row['start_date']} | {row['end_date']} | "
            f"{row['rows']:,} | {int(row['news_count'] or 0):,} |"
        )

    lines.extend(
        [
            "",
            "## Notebook Readiness",
            "",
            f"Ready for notebook analysis: {'yes' if ready else 'no'}",
            "",
            "Criteria used here: at least 300 valid historical news rows in the target window and at least 100 rows with non-null 5-day future returns.",
            "",
            "## Next Steps",
            "",
        ]
    )
    if ready:
        lines.append("1. Run statistical notebooks and inspect whether signal strength is meaningful before backtesting.")
    else:
        lines.append("1. Add more historical Yahoo news or import a curated CSV with `backend/scripts/manual_news_import.py`.")
        lines.append("2. Re-run LLM analysis, price refresh, alignment, daily sentiment, exports, and this status report.")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
