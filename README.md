# 台股新聞情緒分析系統

> 生成式人工智慧課程專題 — 以 LLM 驅動的台灣股市新聞自動分析與問答平台

**線上展示**：[https://frontend-chi-beige-37.vercel.app](https://frontend-chi-beige-37.vercel.app)

> ⚠️ 後端部署於 Render 免費方案，閒置 15 分鐘後會自動休眠。首次載入頁面需等待約 30–50 秒讓服務啟動，啟動後即可正常使用。前端頁面會自動偵測冷啟動狀態並顯示倒數計時。

---

## 系統簡介

本系統全自動收集台股相關新聞，透過大型語言模型（LLM）進行情緒分析，並結合 RAG（Retrieval-Augmented Generation）實現多輪新聞問答。每個工作日 08:15（台灣時間）自動執行完整 pipeline，將結果同步至雲端資料庫並更新前端儀表板。

### GenAI 技術應用

| 技術 | 應用場景 | 模型 / 工具 |
|---|---|---|
| Few-shot prompting | 新聞分類、情緒判斷、標的辨識 | Groq / LLaMA 3.3 70B |
| RAG（語意搜尋） | 以自然語言查詢歷史新聞（本地環境） | BAAI/bge-m3 embeddings + cosine similarity |
| RAG（關鍵字搜尋） | 雲端部署環境下的新聞查詢 | PostgreSQL ILIKE |
| 多輪對話 | RAG 問答記憶前 3 輪上下文 | Groq Chat Completions API |
| 文本生成 | 每日市場觀察摘要自動撰寫 | Groq / LLaMA 3.3 70B |
| 建議問題生成 | 每次問答後推薦 2–3 個後續問題 | Groq（JSON schema output） |

---

## 技術架構

| 層級 | 技術 | 說明 |
|---|---|---|
| 前端 | Next.js 15 + TypeScript | App Router、SSR + ISR（2 分鐘快取） |
| UI 元件 | Recharts + lucide-react | 情緒趨勢圖、情緒分布長條圖 |
| 後端 | Python 3.11 + FastAPI | RESTful API，CORS 支援 Vercel |
| 資料庫（本地） | SQLite | 開發與測試用 |
| 資料庫（雲端） | Neon PostgreSQL | 生產環境，psycopg2 連接 |
| LLM | Groq / LLaMA 3.3 70B | 新聞分析、摘要生成、RAG 問答 |
| 嵌入向量 | BAAI/bge-m3（sentence-transformers） | 本地語意搜尋（雲端降級為關鍵字搜尋） |
| 股價資料 | yfinance / FinMind API | 歷史股價、台灣 ETF |
| 新聞來源 | Yahoo 股市新聞（網頁爬蟲） | BeautifulSoup4 |
| CI/CD | GitHub Actions | 每日自動 pipeline |
| 部署 | Vercel + Render | 前端 + 後端 |

---

## 系統架構

```
GitHub Actions（每日 08:15 TW，週一至週五）
    │
    ├── 1. 爬蟲：Yahoo 股市新聞（fetch_news.py）
    ├── 2. LLM 分析：新聞分類 + 情緒 + 標的（analyze_news_with_llm.py）
    ├── 3. 股價更新：yfinance（fetch_prices.py）
    ├── 4. 報酬對齊：新聞情緒 vs 未來 1/3/5 日報酬（align_news_returns.py）
    ├── 5. 每日情緒彙總（build_daily_sentiment.py）
    ├── 6. LLM 每日摘要生成（generate_daily_brief.py）
    ├── 7. 回測執行（run_backtest.py）
    └── 8. RAG 嵌入向量更新（build_embeddings.py）
         │
         ▼
    Neon PostgreSQL（雲端資料庫）
         │
    ┌────┴────┐
    │         │
  Render    Vercel
  FastAPI   Next.js
  後端 API  前端儀表板
```

---

## 功能展示

### 儀表板總覽

- **每日摘要**：LLM 自動生成的市場觀察文字，含市場情緒標籤（偏多 / 偏空）
- **重點觀察**：今日偏多 / 偏空 / 風險提醒標的一覽（最多各 4 個）
- **KPI 指標**：今日新聞數、完成分析數、觀察標的數、市場情緒分數
- **情緒分布圖**：今日新聞正向 / 中立 / 負向比例長條圖
- **近期股市趨勢**：台股漲跌幅（綠線）vs 回推新聞情緒（橘柱）複合圖表
- **最新新聞分析**：逐則顯示標題、情緒類別、分數、LLM 判斷理由

### 新聞問答（RAG）

- 自然語言提問，LLM 綜合新聞標題與內文回答
- **多輪對話**：記憶前 3 輪問答脈絡，支援追問
- 每個答案附來源引用（含情緒標籤、相關分數）+ 2–3 個 LLM 建議的後續問題
- 支援依股票代號、日期區間篩選
- 自動偵測搜尋模式（本地：語意搜尋 / 雲端：關鍵字搜尋）並顯示模式標籤

---

## 本地執行

### 前置需求

- Python 3.11+
- Node.js 18+
- Groq API Key（[免費申請](https://console.groq.com)）

### 後端啟動

```bash
cd backend

# 建立虛擬環境
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 安裝套件（含 sentence-transformers，用於本地 RAG 語意搜尋）
pip install -r requirements-embeddings.txt

# 建立 .env（填入 GROQ_API_KEY）
cp .env.example .env

# 初始化資料庫
python scripts/init_db.py

# 啟動 API server
uvicorn main:app --reload --port 8000
```

### 前端啟動

```bash
cd frontend
npm install

# 設定後端 URL
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local

npm run dev
# 開啟 http://localhost:3000
```

### 執行完整 pipeline（本地）

```bash
cd backend

# 一次執行所有步驟
python scripts/run_daily_update.py

# 或分步執行
python scripts/fetch_news.py --mode latest --limit 50
python scripts/analyze_news_with_llm.py --limit 50
python scripts/fetch_prices.py --source yfinance
python scripts/align_news_returns.py
python scripts/build_daily_sentiment.py
python scripts/generate_daily_brief.py
python scripts/build_embeddings.py
```

`run_daily_update.py` 支援 `--dry-run` 預覽步驟、`--skip-llm` 略過 Groq 呼叫等選項，方便在 token 受限時測試。

---

## API 端點總覽

後端 FastAPI 服務預設運行於 `http://localhost:8000`，文件見 `/docs`。

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/health` | 健康檢查 |
| GET | `/api/news` | 新聞列表（支援 sentiment / news_type 篩選） |
| GET | `/api/news/{id}` | 單則新聞詳情 |
| GET | `/api/sentiment/summary` | 情緒統計摘要 |
| GET | `/api/sentiment/daily` | 每日情緒時序資料 |
| GET | `/api/stocks/{id}/prices` | 個股歷史股價 |
| GET | `/api/analysis/returns` | 新聞情緒 vs 未來報酬對齊資料 |
| GET | `/api/daily-brief/latest` | 最新每日摘要 |
| GET | `/api/daily-brief/history` | 歷史每日摘要列表 |
| GET | `/api/rag/query` | RAG 問答（q, stock, date_from, date_to, top_k） |

---

## 雲端部署架構

| 服務 | 平台 | 說明 |
|---|---|---|
| 前端 | Vercel | Next.js 15，SSR + ISR（2 分鐘快取） |
| 後端 | Render（免費方案） | FastAPI，閒置後自動休眠 |
| 資料庫 | Neon PostgreSQL（免費方案） | AWS us-west-2，與 Render 同區以降低延遲 |
| 自動化 | GitHub Actions | 每個工作日 08:15 TW 執行完整 pipeline |

### GitHub Actions 所需 Secrets

| Secret | 說明 |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL 連線字串 |
| `GROQ_API_KEY` | Groq API 金鑰 |
| `FINMIND_TOKEN` | FinMind 股價資料（選填，不填自動改用 yfinance） |

### Groq 用量限制

使用 Groq 免費方案需注意以下限制：

- TPD（每日 token 限制）每天 UTC 00:00（台灣 08:00）重置
- GitHub Actions 設定於 08:15 TW 執行，確保每次執行時 token 已重置
- LLM 分析步驟加入 `--sleep 10` 避免觸發 TPM（每分鐘 token）限制
- 建議單次分析上限設為 80 則新聞（workflow 預設值）

---

## 專案結構

```
.
├── backend/
│   ├── app/
│   │   ├── crawlers/       # Yahoo 股市新聞爬蟲（BeautifulSoup4）
│   │   ├── llm/            # Groq 客戶端、Few-shot prompt 設計
│   │   ├── rag/            # 嵌入向量、語意搜尋、多輪問答
│   │   ├── analysis/       # 情緒彙總、報酬對齊、回測
│   │   ├── services/       # API 資料服務層
│   │   └── db/             # 資料庫連線（SQLite 本地 / PostgreSQL 雲端）
│   ├── scripts/            # 自動化 pipeline 腳本
│   │   ├── fetch_news.py          # 新聞爬蟲
│   │   ├── analyze_news_with_llm.py  # LLM 情緒分析
│   │   ├── fetch_prices.py        # 股價資料
│   │   ├── align_news_returns.py  # 新聞與報酬對齊
│   │   ├── build_daily_sentiment.py  # 每日情緒彙總
│   │   ├── generate_daily_brief.py   # LLM 每日摘要
│   │   ├── build_embeddings.py    # RAG 嵌入向量
│   │   ├── run_backtest.py        # 回測執行
│   │   └── run_daily_update.py    # 本地一鍵執行 pipeline
│   ├── tests/                     # 單元測試（pytest）
│   ├── main.py                    # FastAPI 應用程式入口
│   ├── requirements.txt           # 完整套件（本地開發）
│   ├── requirements-render.txt    # 精簡套件（Render 部署）
│   └── requirements-embeddings.txt  # 含 sentence-transformers（GitHub Actions）
├── frontend/
│   ├── app/                # Next.js App Router、全域樣式
│   ├── components/
│   │   └── Dashboard.tsx   # 主儀表板（Recharts 圖表、RAG 對話介面）
│   └── lib/
│       └── api.ts          # API 型別定義、fetch 封裝
├── notebooks/              # Jupyter 分析筆記本
│   ├── 01_news_data_check.ipynb          # 新聞資料品質檢查
│   ├── 02_llm_validation.ipynb           # LLM 判斷準確率驗證
│   ├── 03_sentiment_return_analysis.ipynb  # 情緒與報酬相關性分析
│   ├── 04_backtest_result.ipynb          # 回測結果視覺化
│   └── 05_sentiment_returns_analysis.ipynb # 進階情緒報酬分析
├── docs/                   # 專案文件
│   ├── PROJECT_SPEC.md     # 研究問題與設計原則
│   ├── DATA_PIPELINE.md    # 資料流程說明
│   └── MODEL_VALIDATION.md # 模型驗證方法
├── outputs/
│   └── figures/            # 回測圖表（equity curve、drawdown）
└── .github/workflows/
    └── daily_update.yml    # 每日自動化 pipeline
```

---

## Prompt 設計說明

### 新聞分析（Few-shot Prompting）

採用 7 個精心設計的標注範例，涵蓋：

- **正反例對比**：明確示範「台積電的新聞 target 應填 `2330` 而非 `半導體`」
- **五種新聞類型**：`stock / market / industry / macro / other`
- **情緒三分類**：`positive / neutral / negative`
- **信心分數準則**：0.9–1.0（訊號明確）→ 0.0–0.45（與台股關聯極弱）

### RAG 問答

- 系統提示要求先點出結論再補充細節（3–6 句），強制綜合多則新聞
- 輸出 JSON schema：`answer + citations + suggested_questions`
- 多輪對話注入最近 3 輪問答（最多 6 則訊息），控制 token 用量
- 本地環境使用 BAAI/bge-m3 語意嵌入搜尋；雲端部署因記憶體限制改為 PostgreSQL ILIKE 關鍵字搜尋

### 每日摘要生成

- 輸入量化數據（情緒分數、偏多偏空標的、分析筆數）
- LLM 輸出自然語言敘述，`temperature=0.4` 增加語言多樣性
- Fallback：LLM 失敗時自動切換至模板文字，不中斷 pipeline

---

## 研究問題

本專題圍繞以下四個研究問題設計：

1. 台股新聞情緒是否與未來 1 日、3 日、5 日報酬有關？
2. LLM 是否適合判斷台股新聞語境？
3. 個股新聞、大盤新聞與產業新聞是否應分開處理？
4. 將情緒分數轉成投資訊號後，是否能優於基準策略？

分析結果（含統計顯著性）記錄於 `notebooks/` 中，**如實呈現無效或弱效果結果**，不宣稱可穩定預測股價。

---

## 免責聲明

本系統所有分析結果**僅供學術研究與課程展示**，不構成任何投資建議。回測績效基於歷史資料，不代表未來表現。
