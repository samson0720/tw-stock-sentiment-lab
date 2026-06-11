# Data Pipeline

## 環境需求

在 `backend/.env` 中需設定以下環境變數：

```env
GROQ_API_KEY=your_groq_api_key_here
```

Groq 提供免費額度，申請帳號後至 [console.groq.com](https://console.groq.com) 取得 API Key。

---

## 一鍵執行（推薦）

`run_daily_update.py` 整合所有步驟，包含爬新聞、LLM 分析、抓股價、對齊報酬、產出每日摘要。

```powershell
cd backend

# 一鍵執行所有步驟
python scripts/run_daily_update.py

# 參數說明
python scripts/run_daily_update.py --dry-run       # 僅查看計畫，不實際執行
python scripts/run_daily_update.py --skip-llm      # 跳過 LLM 分析（省 API 費用）
python scripts/run_daily_update.py --limit 50      # LLM 分析上限 50 則
```

---

## 逐步執行

若需要單獨執行各步驟，可依序執行以下指令。

### Step 1: 初始化資料庫

```powershell
cd backend
python scripts/init_db.py
```

### Step 2: 爬取新聞

```powershell
python scripts/fetch_news.py --limit 100
```

輸出：

- `raw_news`
- `outputs/tables/raw_news.csv`

### Step 3: LLM 分析新聞

本專案使用 **Groq API** 呼叫雲端 LLM，不需要本地 GPU 或 Ollama。

```powershell
python scripts/analyze_news_with_llm.py --limit 100
```

預設使用模型：`llama-4-scout-17b-16e-instruct`（速度快、成本低）。
若需要更高推理品質，可改用：`qwen-qwq-32b-preview`。

```powershell
# 指定模型
python scripts/analyze_news_with_llm.py --limit 100 --model qwen-qwq-32b-preview
```

輸出：

- `llm_news_analysis`
- `outputs/tables/llm_news_analysis.csv`

> 若 GROQ_API_KEY 未設定或 API 呼叫失敗，預設會啟用規則型 fallback，方便 pipeline 繼續跑完，但正式報告應標明模型來源。

### Step 4: 抓取股價

```powershell
python scripts/fetch_prices.py --stock-ids 2330,0050 --start-date 2024-01-01
```

輸出：

- `stock_prices`
- `outputs/tables/stock_prices.csv`

### Step 5: 對齊新聞與未來報酬

```powershell
python scripts/align_news_returns.py
```

對齊規則：

- 平日 13:30 前：當日交易日
- 平日 13:30 後：下一交易日
- 週末或休市：下一交易日

輸出：

- `aligned_news_returns`
- `outputs/tables/aligned_news_returns.csv`

### Step 6: 建立日度情緒

```powershell
python scripts/build_daily_sentiment.py
```

輸出：

- `daily_sentiment`
- `outputs/tables/daily_sentiment.csv`

### Step 7: 產生每日摘要

```powershell
python scripts/generate_daily_brief.py
```

此步驟匯總當日情緒訊號，產出市場整體多空判斷與重點觀察標的，寫入 `daily_brief` 資料表。前端 Dashboard 的「今日摘要」與「重點觀察」區塊即來自此輸出。

輸出：

- `daily_brief`（資料庫）

### Step 8: 回測

```powershell
python scripts/run_backtest.py
```

輸出：

- `backtest_results`
- `outputs/tables/backtest_equity_curve.csv`
- `outputs/tables/backtest_metrics.csv`

> **注意：** 回測需要足夠的歷史資料才具統計意義。樣本少於 252 個交易日（約一年）時，Sharpe Ratio 與年化報酬等年化指標屬短期外推，不宜作為策略評估依據。

---

## LLM 模型選擇說明

| 模型 | 特性 | 適用場景 |
|------|------|----------|
| `llama-4-scout-17b-16e-instruct` | 速度快、成本低 | 日常 pipeline，大量新聞分析 |
| `qwen-qwq-32b-preview` | 推理能力強 | 複雜判斷、需要較高準確率時 |

以上模型皆透過 Groq API 呼叫，需在 `backend/.env` 設定 `GROQ_API_KEY`。
