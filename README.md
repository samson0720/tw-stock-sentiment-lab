# TW Stock Sentiment Lab

台股新聞情緒分析與回測研究專案。此專案使用 Yahoo 股市新聞建立本機資料集，透過離線 LLM pipeline 將新聞轉成結構化的 `news_type`、`target`、`sentiment` 與 `sentiment_score`，再和台股股價資料對齊，檢查情緒訊號與未來報酬、簡單等權重策略之間的關係。

本專案是資料分析與研究工具，不是自動交易系統，也不構成投資建議。

## Research Questions

1. 台股新聞情緒是否和未來 1 日、3 日、5 日報酬有關？
2. LLM 是否能穩定判斷台股新聞的類型、標的與情緒？
3. `market`、`stock`、`industry` 類新聞是否應分開處理？
4. 將日度情緒分數轉成簡單投資訊號後，是否能在樣本內優於 0050 benchmark？
5. 在資料量有限、標的 mapping 尚未完全穩定的條件下，哪些結果可以視為研究線索，哪些不能過度解讀？

## Architecture And Pipeline

系統以 SQLite 作為本機資料庫，所有核心分析都透過 script 或 notebook 離線執行。FastAPI 和 frontend 只讀取已處理資料，不直接呼叫 Groq。

```text
Yahoo news / manual CSV
        |
        v
raw_news
        |
        v
analyze_news_with_llm.py  ->  llm_news_analysis
        |
        v
fetch_prices.py           ->  stock_prices
        |
        v
align_news_returns.py     ->  aligned_news_returns
        |
        v
build_daily_sentiment.py  ->  daily_sentiment
        |
        v
notebooks / run_backtest.py / reports
```

主要資料表：

| Table | Purpose |
|---|---|
| `raw_news` | 原始新聞標題、內文、URL、發布時間 |
| `llm_news_analysis` | LLM 判斷的新聞類型、標的、情緒、信心分數 |
| `stock_prices` | 台股日資料 |
| `aligned_news_returns` | 新聞依交易日對齊後的 1d/3d/5d future returns |
| `daily_sentiment` | 依標的與交易日聚合的情緒訊號 |
| `human_validation` | 人工驗證資料 |
| `backtest_results` | 回測設定、equity curve、績效指標 |

## Tech Stack

| Area | Tools |
|---|---|
| Language | Python |
| Data | SQLite, pandas, numpy |
| API | FastAPI, uvicorn |
| LLM | Groq chat completions through offline scripts |
| News crawling | requests, BeautifulSoup |
| Price data | FinMind, yfinance, Yahoo chart API fallback |
| Analysis | Jupyter notebooks, scipy, matplotlib, seaborn |
| Frontend prototype | Next.js, React, Recharts |

## Local Setup

```powershell
cd C:\python_data_analysis_final
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
```

Create `backend/.env`:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1
LLM_PROVIDER=groq
LLM_REQUEST_SLEEP_SECONDS=2
LLM_MAX_RETRIES=4
FINMIND_TOKEN=
```

Optional API server:

```powershell
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Pipeline Order

Run steps independently. The LLM step is intentionally offline and incremental: already analyzed `news_id` rows are skipped.

```powershell
cd backend

# 1. Initialize database
python scripts/init_db.py

# 2. Fetch historical news
python scripts/fetch_news.py --mode historical --start-date 2026-03-01 --end-date 2026-05-08 --limit 350

# Optional fallback if Yahoo cannot provide enough history
python scripts/manual_news_import.py ..\outputs\tables\human_curated_news.csv

# 3. Run offline LLM analysis only for pending news
python scripts/analyze_news_with_llm.py --limit 100 --sleep 0

# 4. Export sample for manual validation
python scripts/export_validation_csv.py --limit 100 --output ../outputs/tables/human_validation_sample.csv

# 5. Refresh prices
python scripts/fetch_prices.py --start-date 2026-03-01

# 6. Align news to returns
python scripts/align_news_returns.py

# 7. Build daily sentiment
python scripts/build_daily_sentiment.py

# 8. Run initial backtest
python scripts/run_backtest.py --top-n 5 --signal-column sentiment_ma5 --rebalance-frequency W-FRI --transaction-cost 0

# 9. Export status and tables
python scripts/write_pipeline_status.py
python scripts/export_tables.py
```

## Completed Work

- Historical Yahoo finance/news ingestion with duplicate URL protection.
- Manual news CSV import fallback.
- Offline Groq LLM analysis pipeline.
- Target normalization for common Taiwan tickers and market aliases.
- Price refresh with Yahoo chart fallback.
- News-to-trading-date alignment and 1d/3d/5d future return calculation.
- Daily sentiment aggregation.
- Sentiment-return analysis notebook:
  - `notebooks/03_sentiment_return_analysis.ipynb`
- Initial backtest notebook:
  - `notebooks/04_backtest_result.ipynb`
- LLM validation workflow notebook:
  - `notebooks/02_llm_validation.ipynb`
- Backtest result persistence in `backtest_results`.

Current pipeline snapshot:

| Metric | Value |
|---|---:|
| `raw_news` | 570 |
| `llm_news_analysis` | 426 success / 0 failed / 144 pending |
| `stock_prices` | 2,687 |
| `aligned_news_returns` | 304 |
| `future_return_1d` non-null | 304 / 304 |
| `future_return_3d` non-null | 304 / 304 |
| `future_return_5d` non-null | 231 / 304 |
| `daily_sentiment` | 46 |

## Preliminary Results

Sentiment-return analysis found weak relationships:

| Horizon | Pearson correlation |
|---|---:|
| 1d | 0.0750 |
| 3d | 0.0795 |
| 5d | -0.0403 |

Initial observations:

- Sentiment score has a weak positive correlation with 1d and 3d future returns.
- The 5d relationship weakens and turns slightly negative in the current sample.
- Positive sentiment rows have slightly higher average 1d/3d returns than negative sentiment rows, but the effect is small.

Initial backtest:

| Metric | Strategy | 0050 Benchmark |
|---|---:|---:|
| Total return | 14.36% | 7.22% |
| Max drawdown | -6.29% | -5.32% |
| Rebalances | 3 | 0 |
| Period | 2026-04-29 to 2026-05-22 | 2026-04-29 to 2026-05-22 |

These results are from a short sample period and should not be treated as evidence of a deployable trading strategy. Annualized metrics and Sharpe ratios are especially unstable because the test window is short.

## LLM Validation Workflow

The project includes a validation workflow in:

```text
notebooks/02_llm_validation.ipynb
```

Current status:

- `human_validation` is not filled yet.
- `outputs/tables/human_validation_sample.csv` is prepared for teammates to label manually.
- The validation notebook does not fabricate accuracy numbers.
- Until human labels are filled, model quality should be treated as unverified.

After teammates fill `human_news_type`, `human_target`, and `human_sentiment`, rerun the notebook to generate:

- `outputs/tables/llm_validation_summary.csv`
- `outputs/tables/llm_misclassified_examples.csv`
- `outputs/figures/llm_validation_accuracy.png`
- `outputs/figures/llm_validation_confusion_matrix.png`

## Project Limitations

- The current sample is small and concentrated in a short 2026 window.
- 144 news rows are still pending LLM analysis.
- Human validation is not complete, so LLM labeling accuracy is not yet measured.
- Target mapping is useful but incomplete; industry and ETF labels need more cleanup.
- Some ticker price data may fail depending on exchange suffix or data source availability.
- The initial backtest has only 3 rebalances and no transaction costs.
- Current results are exploratory and should not be interpreted as investment advice.

## Future Work

- Collect more historical news across multiple market regimes.
- Complete human validation and quantify LLM accuracy.
- Improve target mapping for ETFs, OTC tickers, aliases, and industry labels.
- Add transaction costs, turnover analysis, and slippage assumptions.
- Add out-of-sample and walk-forward validation.
- Explore Black-Litterman only after the signal quality and target coverage are better understood.
- Build a dashboard after the research pipeline is stable.

## Repository Notes

Ignored local artifacts include:

- `.env`
- SQLite database files under `backend/data/`
- generated CSV files under `outputs/tables/`
- generated figures under `outputs/figures/`
- logs, caches, and `__pycache__`

This keeps Git focused on source code, notebooks, and reproducible workflow definitions.
