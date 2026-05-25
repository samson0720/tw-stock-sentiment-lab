from app.db.database import connect


LLM_ANALYSIS_COLUMNS = {
    "status": "TEXT NOT NULL DEFAULT 'success'",
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
        or "'ignore'" in table_sql
        or "'etf'" not in table_sql
        or "'macro'" not in table_sql
        or "'other'" not in table_sql
    )
    if not needs_rebuild:
        return

    conn.execute("ALTER TABLE llm_news_analysis RENAME TO llm_news_analysis_old")
    conn.execute(
        """
        CREATE TABLE llm_news_analysis (
            news_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'success' CHECK(status IN ('success', 'failed')),
            news_type TEXT CHECK(news_type IN ('stock', 'etf', 'market', 'industry', 'macro', 'other')),
            target_type TEXT CHECK(target_type IN ('stock', 'etf', 'index', 'industry', 'commodity', 'macro', 'company_foreign', 'other')),
            target TEXT,
            target_name TEXT,
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

    def old_column(name: str, fallback: str) -> str:
        return name if name in old_columns else fallback

    target_type_expr = (
        "target_type"
        if "target_type" in old_columns
        else """
        CASE
            WHEN news_type = 'stock' THEN 'stock'
            WHEN news_type = 'market' THEN 'index'
            WHEN news_type = 'industry' THEN 'industry'
            ELSE 'other'
        END
        """
    )
    target_name_expr = "target_name" if "target_name" in old_columns else "''"
    conn.execute(
        f"""
        INSERT INTO llm_news_analysis
        (news_id, status, news_type, target_type, target, target_name, sentiment, confidence, reason,
         sentiment_score, model_name, prompt_version, raw_response, error_message, processed_at)
        SELECT
            news_id,
            {old_column("status", "'success'")},
            CASE WHEN news_type = 'ignore' THEN 'other' ELSE news_type END,
            {target_type_expr},
            CASE WHEN news_type = 'ignore' THEN NULL ELSE target END,
            {target_name_expr},
            sentiment,
            confidence,
            reason,
            sentiment_score,
            model_name,
            {old_column("prompt_version", "'twstock-news-v1'")},
            {old_column("raw_response", "NULL")},
            {old_column("error_message", "NULL")},
            {old_column("processed_at", "datetime('now')")}
        FROM llm_news_analysis_old
        """
    )
    conn.execute("DROP TABLE llm_news_analysis_old")


def migrate() -> None:
    with connect() as conn:
        _migrate_llm_news_analysis(conn)
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
