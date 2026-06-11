CREATE TABLE IF NOT EXISTS raw_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL,
    published_at TEXT,
    url TEXT NOT NULL UNIQUE,
    crawled_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_news_analysis (
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
);

CREATE TABLE IF NOT EXISTS stock_prices (
    stock_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume REAL,
    source TEXT NOT NULL,
    PRIMARY KEY(stock_id, date)
);

CREATE TABLE IF NOT EXISTS aligned_news_returns (
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
);

CREATE TABLE IF NOT EXISTS daily_sentiment (
    target TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    news_count INTEGER NOT NULL,
    sentiment_avg REAL NOT NULL,
    sentiment_sum REAL NOT NULL,
    positive_count INTEGER NOT NULL,
    neutral_count INTEGER NOT NULL,
    negative_count INTEGER NOT NULL,
    positive_ratio REAL NOT NULL,
    negative_ratio REAL NOT NULL,
    avg_confidence REAL NOT NULL,
    sentiment_ma3 REAL,
    sentiment_ma5 REAL,
    sentiment_ma20 REAL,
    PRIMARY KEY(target, trading_date)
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    config TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    equity_curve TEXT NOT NULL,
    metrics TEXT NOT NULL,
    created_at TEXT NOT NULL
);

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
);

CREATE TABLE IF NOT EXISTS human_validation (
    news_id INTEGER PRIMARY KEY,
    human_news_type TEXT,
    human_target TEXT,
    human_sentiment TEXT,
    llm_news_type TEXT,
    llm_target TEXT,
    llm_sentiment TEXT,
    type_correct INTEGER,
    sentiment_correct INTEGER,
    note TEXT,
    FOREIGN KEY(news_id) REFERENCES raw_news(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS news_embeddings (
    news_id INTEGER PRIMARY KEY,
    stock_id TEXT,
    published_at TEXT,
    embedding BLOB NOT NULL,
    FOREIGN KEY(news_id) REFERENCES raw_news(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_raw_news_published_at ON raw_news(published_at);
CREATE INDEX IF NOT EXISTS idx_news_embeddings_stock ON news_embeddings(stock_id);
CREATE INDEX IF NOT EXISTS idx_news_embeddings_date ON news_embeddings(published_at);
CREATE INDEX IF NOT EXISTS idx_llm_news_type ON llm_news_analysis(news_type);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_date ON stock_prices(stock_id, date);
CREATE INDEX IF NOT EXISTS idx_aligned_target_date ON aligned_news_returns(target, trading_date);
CREATE INDEX IF NOT EXISTS idx_daily_sentiment_target_date ON daily_sentiment(target, trading_date);
CREATE INDEX IF NOT EXISTS idx_daily_brief_date ON daily_brief(brief_date);
