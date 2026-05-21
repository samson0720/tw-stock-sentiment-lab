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
