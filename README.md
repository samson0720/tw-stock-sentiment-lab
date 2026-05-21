# 台股新聞情緒分析與投資組合研究平台

本專案是一套全本機執行的 Python 資料分析系統，用 Yahoo 奇摩股市新聞建立新聞資料集，透過 Groq LLM 離線批次判斷新聞類型、標的與情緒，再將情緒因子和台股股價的未來報酬對齊，進行統計分析與簡單回測。

本專案是研究與資料分析工具，不構成投資建議。

## 目前完成範圍

- SQLite schema：`raw_news`、`llm_news_analysis`、`stock_prices`、`aligned_news_returns`、`daily_sentiment`、`human_validation`、`backtest_results`
- Yahoo 奇摩股市新聞爬蟲
- Groq LLM 離線批次分析，支援 API key、retry、sleep、已分析快取、JSON 失敗保存
- 人工驗證 CSV 匯出
- FinMind 股價抓取，yfinance 備援
- 新聞發布時間對齊交易日
- 未來 1 日、3 日、5 日報酬計算
- 日度情緒聚合與移動平均
- FastAPI 讀取已處理資料
- 簡單情緒策略回測骨架

## 快速開始

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
```

建立 `backend/.env`：

```text
GROQ_API_KEY=你的 Groq API key
GROQ_MODEL=llama-3.1-8b-instant
LLM_REQUEST_SLEEP_SECONDS=2
LLM_MAX_RETRIES=4
FINMIND_TOKEN=
```

## Pipeline

每個步驟都可單獨執行。LLM 不會在前端或 API 啟動時被呼叫。

```powershell
cd backend
python scripts/fetch_news.py --limit 100
python scripts/analyze_news_with_llm.py --limit 100
python scripts/export_validation_csv.py --limit 100
python scripts/fetch_prices.py --stock-ids 2330,0050 --start-date 2024-01-01
python scripts/align_news_returns.py
python scripts/build_daily_sentiment.py
python scripts/export_tables.py
python scripts/run_backtest.py
```

啟動後端：

```powershell
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API 預設網址：`http://localhost:8000`

## Groq 使用量設計

`scripts/analyze_news_with_llm.py` 只分析尚未存在於 `llm_news_analysis` 的 `news_id`。每次請求會套用 sleep 與 retry；遇到 429、5xx 或暫時性錯誤會等待後重試。若模型輸出不是合法 JSON，系統會將 `status` 標記為 `failed`，保留 `raw_response` 與 `error_message` 方便人工檢查。

## 資料輸出

中間表可用下列指令輸出為 CSV：

```powershell
cd backend
python scripts/export_tables.py
```

人工驗證樣本：

```powershell
python scripts/export_validation_csv.py --limit 200
```

輸出位置：`outputs/tables/`
