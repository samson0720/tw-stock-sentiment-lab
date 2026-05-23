from __future__ import annotations

from pathlib import Path
import argparse
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> None:
    command = [sys.executable, str(ROOT / "scripts" / args[0]), *args[1:]]
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local daily data update pipeline.")
    parser.add_argument("--news-limit", type=int, default=120)
    parser.add_argument("--llm-limit", type=int, default=80)
    parser.add_argument("--llm-sleep", type=float, default=0)
    parser.add_argument("--price-start-date", default="2026-03-01")
    parser.add_argument("--price-source", choices=["finmind", "yfinance"], default="finmind")
    parser.add_argument("--skip-llm", action="store_true", help="Fetch and rebuild from existing analysis only.")
    args = parser.parse_args()

    _run(["init_db.py"])
    _run(["fetch_news.py", "--mode", "latest", "--limit", str(args.news_limit)])
    if not args.skip_llm and args.llm_limit > 0:
        _run(["analyze_news_with_llm.py", "--limit", str(args.llm_limit), "--sleep", str(args.llm_sleep)])
    _run(
        [
            "fetch_prices.py",
            "--start-date",
            args.price_start_date,
            "--source",
            args.price_source,
        ]
    )
    _run(["align_news_returns.py"])
    _run(["build_daily_sentiment.py"])
    _run(["generate_daily_brief.py"])
    print("\nDaily update complete.")


if __name__ == "__main__":
    main()
