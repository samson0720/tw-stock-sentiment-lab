# 台股新聞情緒分析與投資組合研究平台

> **Taiwan Stock News Sentiment Analysis & Portfolio Research Platform**
>
> 大學期末專題 — 全本機執行的 NLP 情緒因子研究系統

---

## 目錄 (Table of Contents)

1. [專案簡介](#1-專案簡介)
2. [研究動機與問題](#2-研究動機與問題)
3. [系統架構](#3-系統架構)
4. [技術棧](#4-技術棧)
5. [快速開始](#5-快速開始)
6. [開發環境設置](#6-開發環境設置)
7. [資料 Pipeline 說明](#7-資料-pipeline-說明)
8. [API 文件](#8-api-文件)
9. [專案結構](#9-專案結構)
10. [資料現況與初步結果](#10-資料現況與初步結果)
11. [限制與誠實說明](#11-限制與誠實說明)
12. [授權](#12-授權)

---

## 1. 專案簡介

本專案是一套**全本機執行**的台股新聞情緒分析與投資組合研究平台，作為大學資料分析課程期末專題。

核心流程如下：

```
Yahoo Finance Taiwan 新聞爬取
        ↓
  LLM 結構化情緒分析 (Groq API)
        ↓
  情緒因子正規化 / 對齊交易日
        ↓
  情緒 × 未來報酬相關性分析
        ↓
  回測：情緒訊號 vs. 基準策略 (0050)
        ↓
  Next.js 儀表板視覺化
```

本系統**不宣稱可穩定預測股價**，亦不構成任何投資建議。所有分析結果（包含無效或弱效果）均如實呈現。

---

## 2. 研究動機與問題

### 研究動機

隨著 Large Language Model (LLM) 技術成熟，將新聞文字轉換為結構化情緒因子的成本大幅降低。然而，針對**台股中文語境**的 LLM 情緒分析效果，仍缺乏系統性的學術驗證。本研究嘗試建立一套可重現的本機研究流程，探討 LLM 情緒因子在台股短期報酬預測上的實際效果。

> With the maturity of LLM technology, converting news text into structured sentiment factors has become increasingly accessible. However, systematic validation of LLM sentiment analysis in the **Traditional Chinese / Taiwan stock market context** remains limited. This project builds a fully local, reproducible research pipeline to examine whether LLM-derived sentiment factors carry predictive power for short-term Taiwan stock returns.

### 研究問題

| # | 研究問題 |
|---|---------|
| Q1 | 台股新聞情緒是否與未來 **1 日、3 日、5 日** 報酬有顯著相關？ |
| Q2 | LLM 是否適合判斷台股新聞語境下的情緒方向？（透過人工抽樣驗證） |
| Q3 | **個股新聞、大盤新聞、產業新聞**是否應分開分析，其情緒效果是否不同？ |
| Q4 | 將情緒分數轉換為交易訊號後，是否能優於買進持有基準策略（0050）？ |

---

## 3. 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Frontend)                         │
│              Next.js 14  ·  TypeScript  ·  Recharts          │
│                    http://localhost:3000                      │
└────────────────────────┬────────────────────────────────────┘
                         │  REST API (JSON)
┌────────────────────────▼────────────────────────────────────┐
│                     後端 (Backend)                           │
│              FastAPI  ·  Python 3.12  ·  uvicorn             │
│                    http://localhost:8000                      │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   crawlers/  │  │    llm/      │  │    analysis/     │   │
│  │ Yahoo News   │  │  Groq API    │  │ returns, scoring │   │
│  │   scraper    │  │  prompts v6  │  │ targets, daily   │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                   │              │
│  ┌──────▼─────────────────▼───────────────────▼──────────┐  │
│  │              SQLite Database                           │  │
│  │         backend/data/twstock_sentiment.db              │  │
│  │                                                        │  │
│  │  raw_news │ llm_news_analysis │ stock_prices           │  │
│  │  aligned_news_returns │ daily_sentiment │ daily_brief  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────┐   ┌────────────────────────────┐   │
│  │     backtest/       │   │         scripts/           │   │
│  │ strategies, metrics │   │  run_daily_update.py (主)  │   │
│  └─────────────────────┘   └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              外部資料來源 (External Data Sources)             │
│   Yahoo Finance TW (爬蟲) │ Groq API │ yfinance │ FinMind   │
└─────────────────────────────────────────────────────────────┘
```

### 資料庫 Schema 概覽

| 資料表 | 說明 |
|--------|------|
| `raw_news` | 爬取的原始新聞（標題、內文、來源、發布時間） |
| `llm_news_analysis` | LLM 分析結果（新聞類型、標的、情緒、信心分數、prompt 版本） |
| `stock_prices` | 股票日收盤價（yfinance / FinMind） |
| `aligned_news_returns` | 新聞情緒 × 未來報酬對齊表（1d/3d/5d future return） |
| `daily_sentiment` | 每日情緒聚合（sentiment_avg, sentiment_ma5, 各類別計數） |
| `daily_brief` | 每日市場情緒摘要 |
| `backtest_results` | 回測績效記錄 |
| `human_validation` | 人工抽樣標註（用於 LLM 準確率評估） |

---

## 4. 技術棧

### Backend

| 元件 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 主要語言 |
| FastAPI | 0.115 | REST API 框架 |
| uvicorn | 0.34 | ASGI 伺服器 |
| SQLite | 內建 | 本機資料庫（WAL mode） |
| pandas | 2.2 | 資料處理與分析 |
| numpy | 2.2 | 數值計算 |
| scipy | 1.14 | 統計檢定 |
| requests / BeautifulSoup4 | — | 新聞爬蟲 |
| yfinance | 0.2 | 股價資料（Yahoo Finance） |
| FinMind | 1.7 | 股價資料（台灣本土） |
| matplotlib / seaborn | — | 靜態圖表 |

### LLM 分析

| 元件 | 說明 |
|------|------|
| **Groq API** | 推論服務（免費 tier 可用） |
| `llama-3.3-70b-versatile` | 主要使用模型（推理品質佳） |
| `llama-3.1-8b-instant` | 輕量備用模型（速度快） |
| Prompt version | `twstock-news-v7`（含 few-shot 示例 + 信心校準指引） |
| Fallback | LLM API 失敗時記錄 `status=fallback`（rules-fallback），不偽造分析結果 |

### Frontend

| 元件 | 版本 | 用途 |
|------|------|------|
| Next.js | 14 | React 框架（App Router） |
| TypeScript | — | 型別安全 |
| Recharts | — | 互動式圖表 |
| Node.js | 18+ | 執行環境 |

---

## 5. 快速開始

### 前置需求

- Python 3.12+
- Node.js 18+
- Groq API Key（免費，申請：https://console.groq.com）

### 一鍵啟動（開發模式）

```powershell
# 複製環境變數設定
Copy-Item backend\.env.example backend\.env
# 編輯 backend\.env，填入 GROQ_API_KEY

# 安裝 Python 依賴
cd backend
pip install -r requirements.txt

# 初始化資料庫並執行完整 pipeline
python scripts/init_db.py
python scripts/run_daily_update.py

# 啟動後端 API（另開終端機）
uvicorn main:app --reload --port 8000

# 啟動前端（另開終端機）
cd ..\frontend
npm install
npm run dev
```

啟動後：

- 前端儀表板：http://localhost:3000
- 後端 API 文件（Swagger UI）：http://localhost:8000/docs
- 後端 API 文件（ReDoc）：http://localhost:8000/redoc

---

## 6. 開發環境設置

### 6.1 環境變數設定

複製 `backend/.env.example` 為 `backend/.env` 並填入以下設定：

```env
# 必填
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 選填（可保留預設值）
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq
LLM_REQUEST_SLEEP_SECONDS=1
LLM_MAX_RETRIES=4

# 選填（若使用 FinMind 資料來源）
FINMIND_TOKEN=
```

> **注意**：`GROQ_API_KEY` 為必填項目。Groq 提供免費 tier，申請網址：https://console.groq.com

### 6.2 Python 虛擬環境（建議）

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
cd backend
pip install -r requirements.txt
```

### 6.3 前端安裝

```powershell
cd frontend
npm install
```

### 6.4 資料庫位置

```
backend/data/twstock_sentiment.db
```

資料庫使用 SQLite（WAL mode），無需額外安裝資料庫軟體。

---

## 7. 資料 Pipeline 說明

整個研究流程分為以下步驟，可逐步執行或使用 `run_daily_update.py` 一次跑完。

### Step 1 — 初始化資料庫

```powershell
cd backend
python scripts/init_db.py
```

建立所有 SQLite 資料表及 migration。

---

### Step 2 — 爬取台股新聞

```powershell
# 最新新聞模式（每日更新用）
python scripts/fetch_news.py --mode latest --limit 120

# 歷史新聞模式（初次建立資料集用）
python scripts/fetch_news.py --mode historical --start-date 2026-03-01 --end-date 2026-05-08 --limit 500
```

**資料來源**：Yahoo Finance Taiwan（RSS feed、個股新聞頁、Finance Stream API）

**爬取策略**：
- RSS feed 取得最新新聞
- 個股頁爬取熱門標的（0050, 2330, 2317, 2454, 2303）
- Finance Stream API 關鍵字搜尋取得歷史新聞
- 以 URL 去重，避免重複收錄

**輸出**：`raw_news` 資料表

---

### Step 3 — LLM 情緒分析

```powershell
# 分析待處理的新聞（使用 Groq API）
python scripts/analyze_news_with_llm.py --limit 80

# 重新分析舊版 prompt 的結果
python scripts/analyze_news_with_llm.py --limit 80 --reanalyze-old-prompts

# 指定模型
python scripts/analyze_news_with_llm.py --limit 80 --model llama-3.3-70b-versatile
```

**Prompt 版本**：`twstock-news-v7`，含 few-shot 示例與信心校準指引，輸出結構化 JSON：

```json
{
  "news_type": "stock | etf | market | industry | macro | other",
  "target_type": "stock | etf | index | industry | ...",
  "target": "主要標的代號或名稱",
  "target_name": "繁體中文標的名稱",
  "targets": [
    {
      "target_type": "...",
      "target": "...",
      "sentiment": "positive | neutral | negative",
      "confidence": 0.85,
      "reason": "不超過 40 字的說明"
    }
  ],
  "sentiment": "positive | neutral | negative",
  "confidence": 0.85,
  "reason": "不超過 40 字的說明"
}
```

**情緒分數計算**：`sentiment_score = direction × confidence`

- `positive` → direction = +1.0
- `neutral` → direction = 0.0
- `negative` → direction = −1.0

**輸出**：`llm_news_analysis` 資料表

> **重要**：若 LLM API 呼叫失敗，系統會記錄 `status=fallback`（model: rules-fallback），**不會**偽造分析結果。正式報告中的分析僅包含 `status=success` 的資料列。

---

### Step 4 — 抓取股票價格

```powershell
# 使用 FinMind（推薦，台股本土資料）
python scripts/fetch_prices.py --start-date 2026-03-01 --source finmind

# 使用 yfinance（不需 token）
python scripts/fetch_prices.py --start-date 2026-03-01 --source yfinance

# 指定個股
python scripts/fetch_prices.py --stock-ids 2330,0050,2317 --start-date 2026-01-01
```

**追蹤標的**：自動從 `llm_news_analysis` 擷取所有出現過的股票代號，加上核心必追蹤股：`0050, 2330, 2317, 2454, 2303, 3481`

**輸出**：`stock_prices` 資料表

---

### Step 5 — 對齊新聞與未來報酬

```powershell
python scripts/align_news_returns.py
```

將每則已分析新聞對齊至最近的交易日，計算：

| 欄位 | 說明 |
|------|------|
| `future_return_1d` | 對齊日後第 1 個交易日報酬 |
| `future_return_3d` | 對齊日後第 3 個交易日報酬 |
| `future_return_5d` | 對齊日後第 5 個交易日報酬 |

**交易日對齊規則**：

- 平日 13:30 前發布 → 當日交易日
- 平日 13:30 後發布 → 下一交易日
- 週末 / 休市 → 下一交易日

**輸出**：`aligned_news_returns` 資料表

---

### Step 6 — 建立每日情緒聚合

```powershell
python scripts/build_daily_sentiment.py
```

依標的（target）× 交易日聚合，計算：

- `sentiment_avg`：當日平均情緒分數
- `sentiment_ma5`：5 日移動平均情緒分數
- `positive_count / neutral_count / negative_count`：各情緒類別計數
- `positive_ratio / negative_ratio`：比例
- `avg_confidence`：平均信心分數

**輸出**：`daily_sentiment` 資料表

---

### Step 7 — 生成每日市場摘要

```powershell
python scripts/generate_daily_brief.py

# 指定日期
python scripts/generate_daily_brief.py --date 2026-05-08
```

根據當日情緒數據生成市場觀察摘要，包含：情緒偏多/偏空/中性判斷、情緒偏多前五大標的、情緒偏空前五大標的、風險提醒標的（負向情緒比例偏高或出現高信心負向新聞）。

**輸出**：`daily_brief` 資料表

---

### Step 8 — 執行回測

```powershell
python scripts/run_backtest.py
```

**策略**：高情緒等權重週度再平衡策略

- 每週五（或最後交易日）選出情緒分數（`sentiment_ma5`）最高的前 N 檔（預設 5 檔）
- 等權重持有至下次再平衡
- 基準：0050（台灣50 ETF）
- 交易成本：預設 0（研究用途，不含滑價）

**輸出**：`backtest_results` 資料表、`outputs/tables/backtest_equity_curve.csv`

---

### 一鍵執行完整 Pipeline

```powershell
cd backend

# 完整更新（爬蟲 + LLM + 股價 + 對齊 + 聚合 + 摘要）
python scripts/run_daily_update.py

# 空跑模式（只顯示計劃，不實際寫入或呼叫 API）
python scripts/run_daily_update.py --dry-run

# 跳過 LLM（只更新股價與下游計算）
python scripts/run_daily_update.py --skip-llm

# 控制 LLM 分析上限與新聞爬取上限
python scripts/run_daily_update.py --limit 50 --news-limit 120

# 重新分析舊版 prompt 的資料
python scripts/run_daily_update.py --reanalyze-old-prompts
```

---

## 8. API 文件

後端啟動後，完整互動式文件請見：http://localhost:8000/docs

### 健康檢查

```
GET /api/health
```

```json
{ "status": "ok" }
```

---

### 新聞列表

```
GET /api/news?limit=100&news_type=stock&sentiment=positive
```

| 參數 | 類型 | 說明 |
|------|------|------|
| `limit` | int (1–1000) | 返回筆數，預設 100 |
| `news_type` | string | 篩選：`stock / etf / market / industry / macro / other` |
| `sentiment` | string | 篩選：`positive / neutral / negative` |

---

### 單則新聞詳情

```
GET /api/news/{news_id}
```

---

### 情緒統計摘要

```
GET /api/sentiment/summary
```

返回整體情緒分布統計（各類型、各情緒的計數與比例）。

---

### 每日情緒時序

```
GET /api/sentiment/daily?target=2330&limit=500
```

| 參數 | 類型 | 說明 |
|------|------|------|
| `target` | string | 篩選特定標的，例如 `2330`、`0050` |
| `limit` | int (1–5000) | 返回筆數，預設 500 |

---

### 股票列表

```
GET /api/stocks
```

---

### 股票價格時序

```
GET /api/stocks/{stock_id}/prices?limit=500
```

---

### 新聞報酬對齊資料

```
GET /api/analysis/returns?limit=2000
```

返回 `aligned_news_returns` 全部資料（情緒分數 + 未來 1/3/5 日報酬），供 Jupyter Notebook 相關性分析使用。

---

### 回測結果

```
GET /api/backtest/results
```

---

### 最新每日市場摘要

```
GET /api/daily-brief/latest
```

---

### 歷史每日市場摘要

```
GET /api/daily-brief/history?limit=30
```

---

## 9. 專案結構

```
python_data_analysis_final/
│
├── backend/
│   ├── main.py                          # FastAPI app 入口點
│   ├── requirements.txt                 # Python 依賴清單
│   ├── .env.example                     # 環境變數範本
│   ├── data/
│   │   └── twstock_sentiment.db         # SQLite 資料庫（gitignore）
│   │
│   ├── app/
│   │   ├── config.py                    # 設定管理（pydantic-settings）
│   │   ├── crawlers/
│   │   │   └── yahoo_news.py            # Yahoo Finance TW 爬蟲
│   │   ├── llm/
│   │   │   ├── groq_client.py           # Groq API 客戶端（含 retry 邏輯）
│   │   │   └── prompts.py               # Prompt 建構（v6，20 條標註規則）
│   │   ├── analysis/
│   │   │   ├── scoring.py               # 情緒分數計算 + 標的正規化
│   │   │   ├── targets.py               # 標的名稱正規化（股票代號對照）
│   │   │   ├── returns.py               # 新聞與未來報酬對齊邏輯
│   │   │   ├── alignment.py             # 交易日對齊工具
│   │   │   └── prices.py                # 股價資料處理
│   │   ├── backtest/
│   │   │   ├── strategies.py            # 回測策略（高情緒等權重策略）
│   │   │   └── metrics.py               # 績效指標計算（Sharpe、MDD 等）
│   │   ├── routers/
│   │   │   └── api.py                   # FastAPI 路由定義
│   │   ├── services/
│   │   │   ├── summary_service.py       # API 資料彙整服務
│   │   │   └── price_service.py         # 股價服務
│   │   └── db/
│   │       ├── database.py              # SQLite 連線管理
│   │       └── migrations.py            # DB schema migrations
│   │
│   └── scripts/
│       ├── run_daily_update.py          # 主 pipeline 協調器
│       ├── init_db.py                   # 資料庫初始化
│       ├── fetch_news.py                # 新聞爬蟲腳本
│       ├── analyze_news_with_llm.py     # LLM 分析腳本
│       ├── fetch_prices.py              # 股價抓取腳本
│       ├── align_news_returns.py        # 對齊腳本
│       ├── build_daily_sentiment.py     # 日度情緒聚合腳本
│       ├── generate_daily_brief.py      # 每日市場摘要腳本
│       ├── run_backtest.py              # 回測腳本
│       ├── export_validation_csv.py     # 匯出驗證樣本
│       └── create_validation_sample.py  # 建立人工標註抽樣檔
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                     # 主頁面
│   │   └── styles.css                   # 全域樣式
│   ├── components/
│   │   └── Dashboard.tsx                # 儀表板主元件
│   └── lib/
│       └── api.ts                       # API 呼叫封裝
│
├── notebooks/
│   └── 01_news_data_check.ipynb         # 資料品質檢查 Notebook
│
├── docs/
│   ├── PROJECT_SPEC.md                  # 專案規格書
│   ├── DATA_PIPELINE.md                 # Pipeline 詳細說明
│   ├── MODEL_VALIDATION.md              # LLM 驗證設計
│   └── REPORT_OUTLINE.md               # 期末報告大綱
│
└── outputs/
    ├── figures/                         # 輸出圖表（.gitkeep）
    ├── tables/                          # 輸出資料表（CSV）
    └── reports/                         # 輸出報告（Markdown）
        └── pipeline_status.md           # 最新 pipeline 狀態
```

---

## 10. 資料現況與初步結果

> 以下為截至 2026-06-11 的資料狀態，持續更新中。

### 資料規模

| 項目 | 數量 |
|------|------|
| 原始新聞 (raw_news) | 1,345 則 |
| LLM 分析成功 | 847 則 |
| LLM fallback（API 失敗） | 468 則 |
| 待分析 (pending) | 30 則 |
| 股票價格資料 | 4,734 筆（44 檔股票） |
| 新聞報酬對齊資料 | 625 筆 |
| 每日情緒聚合 | 143 筆 |

**新聞時間範圍**：2026-03-01 至 2026-05-08

### 情緒分布

| 情緒 | 則數 | 比例 |
|------|------|------|
| neutral（中性） | 230 | 44% |
| positive（正向） | 191 | 37% |
| negative（負向） | 102 | 19% |

### 新聞類型分布

| 類型 | 則數 |
|------|------|
| market（大盤） | 225 |
| industry（產業） | 180 |
| stock（個股） | 86 |
| other（其他） | 20 |
| macro（總體） | 12 |

### 主要分析標的（Top 5）

| 標的 | 類型 | 新聞則數 |
|------|------|---------|
| market / 0050 | 大盤/ETF | 74 |
| market / TAIEX | 大盤 | 63 |
| market / TAIEX/0050 | 大盤 | 58 |
| stock / 2330（台積電） | 個股 | 24 |
| industry / 半導體 | 產業 | 13 |

### 未來報酬覆蓋率

| 欄位 | 有效筆數 | 覆蓋率 |
|------|---------|--------|
| future_return_1d | 599 | 95.8% |
| future_return_3d | 524 | 83.8% |
| future_return_5d | 443 | 70.9% |

> 5 日報酬覆蓋率低於 1d/3d，原因為部分近期新聞在樣本結束時缺乏足夠後續交易日。

### 初步回測說明

- **回測期間**：2026-04-29 至 2026-05-22（**僅 17 個交易日**）
- **策略**：高情緒等權重週度再平衡，前 5 大情緒標的，基準為 0050
- **重要聲明**：回測期間極短，統計上不具顯著意義，結果**不應**作為任何投資決策依據

### 情緒報酬相關性分析

相關性分析（`sentiment_score` vs. `future_return_1d/3d/5d`）目前進行中，詳見 `notebooks/` 目錄。

**目前觀察**（初步，待完整統計驗證）：

- 樣本量（625 筆對齊資料）涵蓋 44 檔股票，短期分析具初步參考性
- 不同新聞類型（個股 vs. 大盤 vs. 產業）的情緒效果差異尚待系統性分析
- 5 日報酬覆蓋率（70.9%）低於 1d/3d，原因為近期新聞尚無足夠後續交易日

---

## 11. 限制與誠實說明

本節誠實呈現本研究的已知限制，這些限制是學術研究的重要組成部分。

### 研究設計限制

| 限制 | 說明 |
|------|------|
| **樣本期間過短** | 主要分析期間約 2.5 個月（2026-03 至 05），不足以得出穩健的統計結論 |
| **回測期間極短** | 17 個交易日的回測結果幾乎無統計意義，不能代表策略長期表現 |
| **新聞來源單一** | 僅使用 Yahoo Finance Taiwan，未涵蓋公開觀測站、法說會逐字稿、社群討論 |
| **交易成本未納入** | 回測不含券商手續費、證交稅、滑價，實際績效會更低 |
| **樣本偏差** | 爬蟲以熱門搜尋詞為主，可能對台積電（2330）、0050 等大型股過度取樣 |

### LLM 分析限制

| 限制 | 說明 |
|------|------|
| **台股語境挑戰** | LLM 對台股公司名稱、代號、縮寫、慣用語的理解仍有誤判（如「KY 股」、「概念股族群」） |
| **目標標的識別** | 新聞常同時涉及多個標的，LLM 選取「最主要標的」的準確度需人工驗證 |
| **標的標準化困難** | 同一標的出現多種寫法（2330 / 台積電 / TSMC / 2330.TW），需多層正規化規則 |
| **無人工驗證基準** | 截至目前，`human_validation` 資料表尚無標註資料，LLM 準確率未量化 |
| **Prompt 版本演進** | 資料庫中存有 v1 至 v6 多版本 prompt 分析結果，舊版本品質較低 |

### 結果解讀聲明

> **本研究不宣稱 LLM 情緒因子可穩定預測台股股價，亦不構成任何投資建議。**
>
> 若統計分析顯示情緒與報酬的相關性不顯著（p-value > 0.05）或效果量極小，這本身即是研究結論的一部分，而非研究失敗。情緒訊號的弱效果可能反映：市場效率、新聞已被市場定價、LLM 分類誤差、樣本期間偶發性，或台股特有的市場結構。
>
> 所有分析結果均如實呈現，不對結果做選擇性報告（no cherry-picking）。

### 人工驗證現況

LLM 分析品質的量化驗證流程（詳見 `docs/MODEL_VALIDATION.md`）：

```powershell
# 建立 100 則人工標註抽樣檔
cd backend
python scripts/create_validation_sample.py --sample-size 100
# 輸出：outputs/tables/human_validation_sample.csv
```

手動開啟 CSV，填入以下欄位：

| 欄位 | 說明 |
|------|------|
| `human_news_type` | 人工判斷的新聞類型 |
| `human_target` | 人工判斷的主要標的 |
| `human_sentiment` | 人工判斷的情緒方向 |
| `note` | 備注（如誤判原因） |

驗證指標：新聞類型準確率、情緒判斷準確率、常見誤判類型分析（需提供 5–10 個誤判案例）。

---

## 12. 授權

本專案為大學課程學術用途。

- 程式碼：MIT License
- 新聞資料：依 Yahoo Finance 使用條款，僅供學術研究，不得商業使用
- 股價資料：依 yfinance / FinMind 各自的使用條款

---

## 附錄：常見問題

**Q：Groq API rate limit 怎麼處理？**

系統已內建指數退避（exponential backoff）重試邏輯，遇到 HTTP 429 會自動等待並重試最多 4 次。若仍失敗，記錄為 `status=fallback`，不影響已成功的資料。

**Q：可以不用 Groq，改用本機 LLM 嗎？**

可以。在 `.env` 設定 `LLM_PROVIDER=ollama`，並安裝 Ollama（https://ollama.ai）後執行 `ollama pull qwen2.5:7b`，再調整 `OLLAMA_BASE_URL` 設定值。

**Q：前端儀表板顯示空資料怎麼辦？**

確認後端已正常啟動（http://localhost:8000/api/health 應返回 `{"status":"ok"}`），且 pipeline 已至少執行過 Step 1 到 Step 6。

**Q：如何只更新股價，不重新爬新聞和跑 LLM？**

```powershell
python scripts/run_daily_update.py --skip-fetch-news --skip-llm
```

**Q：如何確認 pipeline 執行狀況？**

每次執行 `run_daily_update.py` 後，會在 `outputs/reports/daily_update_status.md` 產生執行報告，包含每個步驟的成功/失敗狀態與統計數字。

---

*本 README 最後更新：2026-06-11*
