from app.db.database import connect


LLM_ANALYSIS_COLUMNS = {
    "status": "TEXT NOT NULL DEFAULT 'success'",
    "prompt_version": "TEXT NOT NULL DEFAULT 'twstock-news-v1'",
    "raw_response": "TEXT",
    "error_message": "TEXT",
}


def migrate() -> None:
    with connect() as conn:
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
