from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
REPORT_PATH = PROJECT_ROOT / "outputs" / "reports" / "daily_update_status.md"

sys.path.insert(0, str(ROOT))

from app.analysis.targets import normalize_target
from app.db.database import connect


@dataclass
class StepResult:
    name: str
    status: str
    command: str = ""
    detail: str = ""


@dataclass
class RunStatus:
    started_at: str
    dry_run: bool
    added_news: int = 0
    llm_analyzed: int = 0
    llm_success: int = 0
    llm_failed: int = 0
    price_updated_targets: int = 0
    daily_brief_date: str | None = None
    errors: list[str] = field(default_factory=list)
    steps: list[StepResult] = field(default_factory=list)


def _log(message: str) -> None:
    print(f"[daily-update] {message}", flush=True)


def _count(query: str, params: tuple[object, ...] = ()) -> int:
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
    return int(row[0] or 0)


def _scalar(query: str, params: tuple[object, ...] = ()) -> str | None:
    with connect() as conn:
        row = conn.execute(query, params).fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _pending_news_count() -> int:
    return _count(
        """
        SELECT COUNT(*)
        FROM raw_news n
        LEFT JOIN llm_news_analysis a ON a.news_id = n.id
        WHERE a.news_id IS NULL
        """
    )


def _planned_price_targets() -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT news_type, target
            FROM llm_news_analysis
            WHERE status = 'success'
              AND news_type IN ('stock', 'market', 'industry')
              AND target IS NOT NULL
            """
        ).fetchall()
    required = {"0050", "2330", "2317", "2454", "2303", "3481"}
    targets = {normalize_target(row["news_type"], row["target"]) for row in rows}
    stock_ids = {str(t) for t in targets if t and str(t).isdigit() and len(str(t)) == 4}
    return sorted(required | stock_ids)


def _latest_daily_brief_date() -> str | None:
    return _scalar("SELECT brief_date FROM daily_brief ORDER BY brief_date DESC, created_at DESC LIMIT 1")


def _latest_daily_sentiment_date() -> str | None:
    return _scalar("SELECT MAX(trading_date) FROM daily_sentiment")


def _run_script(script_name: str, args: list[str], status: RunStatus) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(ROOT / "scripts" / script_name), *args]
    command_text = " ".join(command)
    _log(f"START {script_name}: {command_text}")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.stdout and result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr and result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        message = f"{script_name} failed with exit code {result.returncode}"
        status.errors.append(message)
        status.steps.append(StepResult(script_name, "failed", command_text, message))
        _log(f"FAIL {script_name}")
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
    status.steps.append(StepResult(script_name, "success", command_text))
    _log(f"DONE {script_name}")
    return result


def _dry_step(status: RunStatus, name: str, detail: str) -> None:
    _log(f"DRY-RUN {name}: {detail}")
    status.steps.append(StepResult(name, "dry-run", detail=detail))


def _write_status_report(status: RunStatus) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Daily Update Status",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"Started at: {status.started_at}",
        f"Dry run: {'yes' if status.dry_run else 'no'}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| 新增新聞數 | {status.added_news:,} |",
        f"| 本次 LLM 分析數 | {status.llm_analyzed:,} |",
        f"| LLM 成功 | {status.llm_success:,} |",
        f"| LLM 失敗 | {status.llm_failed:,} |",
        f"| 股價更新標的數 | {status.price_updated_targets:,} |",
        f"| daily_brief 日期 | {status.daily_brief_date or '-'} |",
        f"| 是否有錯誤 | {'yes' if status.errors else 'no'} |",
        "",
        "## Steps",
        "",
        "| Step | Status | Detail |",
        "|---|---|---|",
    ]
    for step in status.steps:
        detail = step.detail or step.command or "-"
        detail = detail.replace("|", "\\|").replace("\n", "<br>")
        lines.append(f"| {step.name} | {step.status} | {detail} |")

    lines.extend(["", "## Errors", ""])
    if status.errors:
        lines.extend(f"- {error}" for error in status.errors)
    else:
        lines.append("None")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _log(f"Wrote {REPORT_PATH}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run the local daily data update pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned steps without DB writes or Groq calls.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum pending news rows to analyze with LLM.")
    parser.add_argument("--news-limit", type=int, default=120)
    parser.add_argument("--llm-limit", type=int, default=80, help="Deprecated alias; use --limit.")
    parser.add_argument("--llm-sleep", type=float, default=0)
    parser.add_argument("--price-start-date", default="2026-03-01")
    parser.add_argument("--price-source", choices=["finmind", "yfinance"], default="finmind")
    parser.add_argument("--skip-llm", action="store_true", help="Do not call Groq; rebuild from existing analysis only.")
    parser.add_argument("--skip-fetch-news", action="store_true", help="Do not fetch latest news.")
    parser.add_argument("--skip-price", action="store_true", help="Do not update stock prices.")
    args = parser.parse_args()

    limit = args.limit if args.limit is not None else args.llm_limit
    status = RunStatus(started_at=datetime.now().isoformat(timespec="seconds"), dry_run=args.dry_run)

    before_news = _count("SELECT COUNT(*) FROM raw_news")
    before_llm_total = _count("SELECT COUNT(*) FROM llm_news_analysis")
    before_llm_success = _count("SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'success'")
    before_llm_failed = _count("SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'failed'")
    pending_before = _pending_news_count()
    planned_price_targets = _planned_price_targets()

    _log(f"Mode: {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    _log(f"Pending news before run: {pending_before:,}")
    _log(f"LLM analyze limit: {limit:,}")

    try:
        if args.dry_run:
            _dry_step(status, "init_db.py", "Would ensure SQLite schema and migrations are present.")
            if args.skip_fetch_news:
                _dry_step(status, "fetch_news.py", "Skipped by --skip-fetch-news.")
            else:
                _dry_step(status, "fetch_news.py", f"Would fetch latest Yahoo news with --limit {args.news_limit}.")
            if args.skip_llm or limit <= 0:
                _dry_step(status, "analyze_news_with_llm.py", "Skipped; no Groq call will be made.")
            else:
                analyze_count = min(limit, pending_before)
                _dry_step(
                    status,
                    "analyze_news_with_llm.py",
                    f"Would analyze up to {analyze_count} pending news rows. Groq is not called in dry-run.",
                )
            if args.skip_price:
                _dry_step(status, "fetch_prices.py", "Skipped by --skip-price.")
            else:
                _dry_step(
                    status,
                    "fetch_prices.py",
                    f"Would update {len(planned_price_targets)} targets from {args.price_start_date} via {args.price_source}.",
                )
            _dry_step(status, "align_news_returns.py", "Would rebuild aligned_news_returns.")
            _dry_step(status, "build_daily_sentiment.py", "Would rebuild daily_sentiment.")
            _dry_step(status, "generate_daily_brief.py", "Would generate daily_brief from processed data.")
            status.daily_brief_date = _latest_daily_sentiment_date() or _latest_daily_brief_date()
            return

        _run_script("init_db.py", [], status)

        if args.skip_fetch_news:
            _log("SKIP fetch_news.py by --skip-fetch-news")
            status.steps.append(StepResult("fetch_news.py", "skipped", detail="Skipped by --skip-fetch-news."))
        else:
            _run_script("fetch_news.py", ["--mode", "latest", "--limit", str(args.news_limit)], status)

        if args.skip_llm or limit <= 0:
            _log("SKIP analyze_news_with_llm.py; Groq will not be called.")
            status.steps.append(StepResult("analyze_news_with_llm.py", "skipped", detail="Skipped by --skip-llm or zero limit."))
        else:
            _run_script("analyze_news_with_llm.py", ["--limit", str(limit), "--sleep", str(args.llm_sleep)], status)

        if args.skip_price:
            _log("SKIP fetch_prices.py by --skip-price")
            status.steps.append(StepResult("fetch_prices.py", "skipped", detail="Skipped by --skip-price."))
        else:
            price_result = _run_script(
                "fetch_prices.py",
                ["--start-date", args.price_start_date, "--source", args.price_source],
                status,
            )
            stored_targets = set(re.findall(r"^([0-9A-Za-z_.-]+): stored \d+ price rows", price_result.stdout, re.MULTILINE))
            status.price_updated_targets = len(stored_targets)

        _run_script("align_news_returns.py", [], status)
        _run_script("build_daily_sentiment.py", [], status)
        _run_script("generate_daily_brief.py", [], status)

    except subprocess.CalledProcessError:
        _log("Pipeline stopped because a step failed.")
    finally:
        after_news = _count("SELECT COUNT(*) FROM raw_news")
        after_llm_total = _count("SELECT COUNT(*) FROM llm_news_analysis")
        after_llm_success = _count("SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'success'")
        after_llm_failed = _count("SELECT COUNT(*) FROM llm_news_analysis WHERE status = 'failed'")
        status.added_news = max(after_news - before_news, 0) if not args.dry_run else 0
        status.llm_analyzed = max(after_llm_total - before_llm_total, 0) if not args.dry_run else 0
        status.llm_success = max(after_llm_success - before_llm_success, 0) if not args.dry_run else 0
        status.llm_failed = max(after_llm_failed - before_llm_failed, 0) if not args.dry_run else 0
        if args.dry_run and not args.skip_price:
            status.price_updated_targets = len(planned_price_targets)
        status.daily_brief_date = status.daily_brief_date or _latest_daily_brief_date()
        _write_status_report(status)
        _log(f"Errors: {len(status.errors)}")
        if status.errors:
            raise SystemExit(1)
        _log("Daily update complete.")


if __name__ == "__main__":
    main()
