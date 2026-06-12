import json

from app.db.database import connect


LLM_ANALYSIS_COLUMNS = {
    "status": "TEXT NOT NULL DEFAULT 'success'",
    "targets": "TEXT NOT NULL DEFAULT '[]'",
    "prompt_version": "TEXT NOT NULL DEFAULT 'twstock-news-v1'",
    "raw_response": "TEXT",
    "error_message": "TEXT",
}


def _migrate_llm_news_analysis(conn) -> None:
    table = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'llm_news_analysis'"
    ).fetchone()
    if not table:
        return
    table_sql = table["sql"] or ""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(llm_news_analysis)").fetchall()}
    needs_rebuild = (
        "target_type" not in existing
        or "target_name" not in existing
        or "targets" not in existing
        or "'ignore'" in table_sql
        or "'etf'" not in table_sql
        or "'macro'" not in table_sql
        or "'region'" not in table_sql
        or "'other'" not in table_sql
        or "'fallback'" not in table_sql
    )
    if not needs_rebuild:
        return

    conn.execute("ALTER TABLE llm_news_analysis RENAME TO llm_news_analysis_old")
    conn.execute(
        """
        CREATE TABLE llm_news_analysis (
            news_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'success' CHECK(status IN ('success', 'failed', 'fallback')),
            news_type TEXT CHECK(news_type IN ('stock', 'etf', 'market', 'industry', 'macro', 'other')),
            target_type TEXT CHECK(target_type IN ('stock', 'etf', 'index', 'industry', 'commodity', 'macro', 'region', 'company_foreign', 'other')),
            target TEXT,
            target_name TEXT,
            targets TEXT NOT NULL DEFAULT '[]',
            sentiment TEXT CHECK(sentiment IN ('positive', 'neutral', 'negative')),
            confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
            reason TEXT NOT NULL DEFAULT '',
            sentiment_score REAL,
            model_name TEXT NOT NULL,
            prompt_version TEXT NOT NULL DEFAULT 'twstock-news-v1',
            raw_response TEXT,
            error_message TEXT,
            processed_at TEXT NOT NULL,
            FOREIGN KEY(news_id) REFERENCES raw_news(id) ON DELETE CASCADE
        )
        """
    )
    old_columns = {row["name"] for row in conn.execute("PRAGMA table_info(llm_news_analysis_old)").fetchall()}

    old_rows = conn.execute("SELECT * FROM llm_news_analysis_old").fetchall()
    output = []
    for row in old_rows:
        news_type = row["news_type"] if "news_type" in old_columns else None
        if news_type == "ignore":
            news_type = "other"
        target = None if news_type == "other" else row["target"] if "target" in old_columns else None
        target_type = row["target_type"] if "target_type" in old_columns else None
        if not target_type:
            target_type = "stock" if news_type == "stock" else "index" if news_type == "market" else "industry" if news_type == "industry" else "other"
        if target_type not in {"stock", "etf", "index", "industry", "commodity", "macro", "region", "company_foreign", "other"}:
            target_type = "other"
        target_name = row["target_name"] if "target_name" in old_columns else ""
        if news_type == "other":
            target_type = "other"
            target_name = ""
        if news_type == "other":
            targets = "[]"
        elif "targets" in old_columns and row["targets"]:
            targets = row["targets"]
        elif target:
            targets = json.dumps(
                [
                    {
                        "target_type": target_type,
                        "target": target,
                        "target_name": target_name or "",
                        "sentiment": row["sentiment"] if "sentiment" in old_columns else "neutral",
                        "confidence": row["confidence"] if "confidence" in old_columns else 0.0,
                        "reason": row["reason"] if "reason" in old_columns else "",
                    }
                ],
                ensure_ascii=False,
            )
        else:
            targets = "[]"
        output.append(
            (
                row["news_id"],
                row["status"] if "status" in old_columns else "success",
                news_type,
                target_type,
                target,
                target_name,
                targets,
                row["sentiment"] if "sentiment" in old_columns else None,
                row["confidence"] if "confidence" in old_columns else None,
                row["reason"] if "reason" in old_columns else "",
                row["sentiment_score"] if "sentiment_score" in old_columns else None,
                row["model_name"] if "model_name" in old_columns else "unknown",
                row["prompt_version"] if "prompt_version" in old_columns else "twstock-news-v1",
                row["raw_response"] if "raw_response" in old_columns else None,
                row["error_message"] if "error_message" in old_columns else None,
                row["processed_at"] if "processed_at" in old_columns else None,
            )
        )
    conn.executemany(
        """
        INSERT INTO llm_news_analysis
        (news_id, status, news_type, target_type, target, target_name, targets, sentiment, confidence, reason,
         sentiment_score, model_name, prompt_version, raw_response, error_message, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
        """,
        output,
    )
    conn.execute("DROP TABLE llm_news_analysis_old")


def _migrate_aligned_news_returns(conn) -> None:
    table = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'aligned_news_returns'"
    ).fetchone()
    if not table:
        return
    table_sql = table["sql"] or ""
    if "PRIMARYKEY(news_id,target)" in table_sql.replace(" ", ""):
        return
    conn.execute("ALTER TABLE aligned_news_returns RENAME TO aligned_news_returns_old")
    conn.execute(
        """
        CREATE TABLE aligned_news_returns (
            news_id INTEGER NOT NULL,
            trading_date TEXT NOT NULL,
            target TEXT NOT NULL,
            news_type TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            future_return_1d REAL,
            future_return_3d REAL,
            future_return_5d REAL,
            PRIMARY KEY(news_id, target),
            FOREIGN KEY(news_id) REFERENCES raw_news(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO aligned_news_returns
        (news_id, trading_date, target, news_type, sentiment_score, future_return_1d, future_return_3d, future_return_5d)
        SELECT news_id, trading_date, target, news_type, sentiment_score, future_return_1d, future_return_3d, future_return_5d
        FROM aligned_news_returns_old
        """
    )
    conn.execute("DROP TABLE aligned_news_returns_old")


def migrate() -> None:
    import os
    if os.getenv("DATABASE_URL"):
        return  # PostgreSQL: schema_pg.sql applied by init_db.py; no SQLite migrations needed
    with connect() as conn:
        _migrate_llm_news_analysis(conn)
        _migrate_aligned_news_returns(conn)
        conn.execute(
            """
            UPDATE llm_news_analysis
            SET status = 'fallback',
                news_type = NULL,
                target_type = NULL,
                target = NULL,
                target_name = NULL,
                targets = '[]',
                sentiment = NULL,
                confidence = NULL,
                reason = '',
                sentiment_score = NULL
            WHERE model_name = 'rules-fallback'
            """
        )
        existing = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(llm_news_analysis)").fetchall()
        }
        for column, ddl in LLM_ANALYSIS_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE llm_news_analysis ADD COLUMN {column} {ddl}")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_brief (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brief_date TEXT NOT NULL UNIQUE,
                market_sentiment_score REAL,
                market_label TEXT NOT NULL,
                top_positive_targets TEXT NOT NULL DEFAULT '[]',
                top_negative_targets TEXT NOT NULL DEFAULT '[]',
                risk_flags TEXT NOT NULL DEFAULT '[]',
                summary_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_brief_date ON daily_brief(brief_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_news_type ON llm_news_analysis(news_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aligned_target_date ON aligned_news_returns(target, trading_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_sentiment_target_date ON daily_sentiment(target, trading_date)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_embeddings (
                news_id INTEGER PRIMARY KEY,
                stock_id TEXT,
                published_at TEXT,
                embedding BLOB NOT NULL,
                FOREIGN KEY(news_id) REFERENCES raw_news(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_embeddings_stock ON news_embeddings(stock_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_embeddings_date ON news_embeddings(published_at)")
