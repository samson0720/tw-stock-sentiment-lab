from __future__ import annotations

from datetime import date
from pathlib import Path
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analysis.targets import normalize_target
from app.db.migrations import migrate
from app.db.database import connect


def _latest_brief_date() -> str:
    with connect() as conn:
        row = conn.execute("SELECT MAX(trading_date) AS brief_date FROM daily_sentiment").fetchone()
        if row and row["brief_date"]:
            return str(row["brief_date"])
        row = conn.execute(
            """
            SELECT MAX(substr(COALESCE(n.published_at, n.crawled_at), 1, 10)) AS brief_date
            FROM raw_news n
            JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE a.status = 'success'
            """
        ).fetchone()
    return str(row["brief_date"]) if row and row["brief_date"] else date.today().isoformat()


def _market_label(score: float | None, news_count: int) -> str:
    if score is None or news_count == 0:
        return "資料不足"
    if score >= 0.2:
        return "情緒偏多"
    if score <= -0.2:
        return "情緒偏空"
    return "觀察中性"


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _daily_rows(brief_date: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT target, trading_date, news_count, sentiment_avg, sentiment_ma5,
                   positive_count, neutral_count, negative_count, positive_ratio,
                   negative_ratio, avg_confidence
            FROM daily_sentiment
            WHERE trading_date = ?
            ORDER BY target
            """,
            (brief_date,),
        ).fetchall()
    return [dict(row) for row in rows]


def _analysis_rows(brief_date: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                n.id AS news_id,
                n.title,
                substr(COALESCE(n.published_at, n.crawled_at), 1, 10) AS news_date,
                a.news_type,
                a.target,
                a.sentiment,
                a.sentiment_score,
                a.confidence,
                a.reason
            FROM raw_news n
            JOIN llm_news_analysis a ON a.news_id = n.id
            WHERE a.status = 'success'
              AND substr(COALESCE(n.published_at, n.crawled_at), 1, 10) = ?
            ORDER BY COALESCE(n.published_at, n.crawled_at) DESC
            """,
            (brief_date,),
        ).fetchall()
    return [dict(row) for row in rows]


def _target_payload(row: dict) -> dict:
    return {
        "target": row["target"],
        "sentiment_score": _round(row["sentiment_avg"]),
        "sentiment_ma5": _round(row["sentiment_ma5"]),
        "news_count": int(row["news_count"] or 0),
        "positive_ratio": _round(row["positive_ratio"]),
        "negative_ratio": _round(row["negative_ratio"]),
    }


def _risk_flags(daily_rows: list[dict], analysis_rows: list[dict]) -> list[dict]:
    flags: list[dict] = []
    allowed_targets = {str(row["target"]) for row in daily_rows}
    seen_targets: set[str] = set()

    for row in daily_rows:
        target = str(row["target"])
        score = float(row["sentiment_avg"])
        negative_ratio = float(row["negative_ratio"])
        news_count = int(row["news_count"] or 0)
        if score <= -0.25 or (news_count >= 2 and negative_ratio >= 0.5):
            seen_targets.add(target)
            flags.append(
                {
                    "target": target,
                    "flag": "風險提醒",
                    "reason": "今日負向情緒比例偏高",
                    "sentiment_score": _round(score),
                    "negative_ratio": _round(negative_ratio),
                    "news_count": news_count,
                }
            )

    for row in analysis_rows:
        if row["sentiment"] != "negative":
            continue
        if row["confidence"] is not None and float(row["confidence"]) < 0.7:
            continue
        target = normalize_target(row["news_type"], row["target"]) or str(row["target"] or "未分類")
        if target not in allowed_targets or target in seen_targets:
            continue
        seen_targets.add(target)
        flags.append(
            {
                "target": target,
                "flag": "風險提醒",
                "reason": "出現高信心負向新聞",
                "sentiment_score": _round(row["sentiment_score"]),
                "confidence": _round(row["confidence"]),
                "example_title": row["title"],
            }
        )

    return flags[:8]


def _summary_text(
    brief_date: str,
    market_label: str,
    market_score: float | None,
    news_count: int,
    analyzed_count: int,
    top_positive: list[dict],
    top_negative: list[dict],
    risk_flags: list[dict],
) -> str:
    if news_count == 0 and analyzed_count == 0:
        return f"{brief_date} 目前沒有足夠的已處理新聞可形成市場觀察，建議先執行每日更新 pipeline。"

    positive_text = "、".join(row["target"] for row in top_positive[:3]) or "資料不足"
    negative_text = "、".join(row["target"] for row in top_negative[:3]) or "資料不足"
    risk_text = "、".join(row["target"] for row in risk_flags[:3]) or "暫無明顯集中風險"
    score_text = "資料不足" if market_score is None else f"{market_score:.2f}"

    return (
        f"{brief_date} 市場觀察：整體市場情緒為「{market_label}」，市場情緒分數 {score_text}。"
        f" 當日已完成 LLM 分析 {analyzed_count} 則，其中 {news_count} 則已對齊到觀察標的。"
        f" 情緒相對偏多的觀察標的包含 {positive_text}；情緒相對偏空的觀察標的包含 {negative_text}。"
        f" 風險提醒標的為 {risk_text}。本摘要僅根據已處理資料產生，不代表買賣或持有建議。"
    )


def generate_daily_brief(brief_date: str | None = None) -> dict:
    migrate()
    selected_date = brief_date or _latest_brief_date()
    daily_rows = _daily_rows(selected_date)
    analysis_rows = _analysis_rows(selected_date)

    market_row = next((row for row in daily_rows if row["target"] == "0050"), None)
    total_news_count = sum(int(row["news_count"] or 0) for row in daily_rows)
    if market_row:
        market_score = float(market_row["sentiment_ma5"] if market_row["sentiment_ma5"] is not None else market_row["sentiment_avg"])
    elif total_news_count:
        weighted_sum = sum(float(row["sentiment_avg"]) * int(row["news_count"] or 0) for row in daily_rows)
        market_score = weighted_sum / total_news_count
    else:
        market_score = None

    top_positive = [
        _target_payload(row)
        for row in sorted(daily_rows, key=lambda r: (float(r["sentiment_avg"]), int(r["news_count"] or 0)), reverse=True)
        if float(row["sentiment_avg"]) > 0
    ][:5]
    top_negative = [
        _target_payload(row)
        for row in sorted(daily_rows, key=lambda r: (float(r["sentiment_avg"]), -int(r["news_count"] or 0)))
        if float(row["sentiment_avg"]) < 0
    ][:5]
    flags = _risk_flags(daily_rows, analysis_rows)
    analyzed_count = len(analysis_rows)
    market_label = _market_label(market_score, total_news_count)
    summary_text = _summary_text(
        selected_date,
        market_label,
        market_score,
        total_news_count,
        analyzed_count,
        top_positive,
        top_negative,
        flags,
    )

    payload = {
        "brief_date": selected_date,
        "market_sentiment_score": _round(market_score),
        "market_label": market_label,
        "top_positive_targets": top_positive,
        "top_negative_targets": top_negative,
        "risk_flags": flags,
        "summary_text": summary_text,
    }

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_brief
            (brief_date, market_sentiment_score, market_label, top_positive_targets,
             top_negative_targets, risk_flags, summary_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(brief_date) DO UPDATE SET
                market_sentiment_score = excluded.market_sentiment_score,
                market_label = excluded.market_label,
                top_positive_targets = excluded.top_positive_targets,
                top_negative_targets = excluded.top_negative_targets,
                risk_flags = excluded.risk_flags,
                summary_text = excluded.summary_text,
                created_at = excluded.created_at
            """,
            (
                payload["brief_date"],
                payload["market_sentiment_score"],
                payload["market_label"],
                json.dumps(payload["top_positive_targets"], ensure_ascii=False),
                json.dumps(payload["top_negative_targets"], ensure_ascii=False),
                json.dumps(payload["risk_flags"], ensure_ascii=False),
                payload["summary_text"],
            ),
        )

    return payload


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="Brief date in YYYY-MM-DD. Defaults to latest daily_sentiment date.")
    args = parser.parse_args()
    brief = generate_daily_brief(args.date)
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
