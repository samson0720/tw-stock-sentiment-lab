# 台股新聞情緒分析系統

> 生成式人工智慧課程專題 — 以 LLM 驅動的台灣股市新聞自動分析與問答平台

**線上展示**：[https://frontend-chi-beige-37.vercel.app](https://frontend-chi-beige-37.vercel.app)

> ⚠️ 後端部署於 Render 免費方案，閒置 15 分鐘後會自動休眠。首次載入頁面需等待約 30–50 秒讓服務啟動，啟動後即可正常使用。

---

## 系統簡介

本系統全自動收集台股相關新聞，透過大型語言模型（LLM）進行情緒分析，並結合 RAG（Retrieval-Augmented Generation）實現多輪新聞問答。每個工作日 08:15 自動執行完整 pipeline，將結果同步至雲端資料庫並更新前端儀表板。

### GenAI 技術應用

| 技術 | 應用場景 | 模型 / 工具 |
|---|---|---|
| Few-shot prompting | 新聞分類、情緒判斷、標的辨識 | Groq / LLaMA 3.3 70B |
| RAG（語意搜尋） | 以自然語言查詢歷史新聞 | BAAI/bge-m3 embeddings + cosine similarity |
| RAG（關鍵字搜尋） | 雲端部署 fallback（無嵌入模型時） | PostgreSQL ILIKE |
| 多輪對話 | RAG 問答記憶前 3 輪上下文 | Groq Chat Completions API |
| 文本生成 | 每日市場觀察摘要自動撰寫 | Groq / LLaMA 3.3 70B |
| 建議問題生成 | 每次問答後推薦 2–3 個後續問題 | Groq（JSON schema output） |

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
- **每日摘要**：LLM 自動生成的市場觀察文字（附「AI 生成」標籤）
- **重點觀察**：偏多 / 偏空 / 風險提醒標的一覽
- **情緒分布圖**：今日新聞正向 / 中立 / 負向比例長條圖
- **近期股市趨勢**：股價漲跌幅 vs 回推新聞情緒

### LLM 預測驗證
- **方向準確率**：LLM 判為正向的新聞，隔日股價上漲的命中率
- **各情緒組別平均報酬**：正向 / 負向 / 中立情緒新聞的平均次日報酬率
- 提供量化依據，驗證 LLM 情緒分析是否具備預測訊號

### 回測績效
- 高情緒分數等權策略 vs 0050 基準比較
- 指標：Sharpe Ratio、年化報酬、最大回撤、勝率
- ⚠️ 目前回測樣本偏短（< 30 交易日），指標統計意義有限

### 新聞問答（RAG）
- 自然語言提問，LLM 綜合新聞標題與內文回答
- **多輪對話**：記憶前 3 輪問答脈絡，支援追問
- 每個答案附來源引用 + 2–3 個 LLM 建議的後續問題
- 支援依股票代號、日期區間篩選
- 自動偵測搜尋模式（語意搜尋 / 關鍵字搜尋）

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
uvicorn app.main:app --reload --port 8000
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
python scripts/fetch_news.py --mode latest --limit 50
python scripts/analyze_news_with_llm.py --limit 50
python scripts/fetch_prices.py --source yfinance
python scripts/align_news_returns.py
python scripts/build_daily_sentiment.py
python scripts/generate_daily_brief.py
python scripts/build_embeddings.py
```

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
| `FINMIND_TOKEN` | FinMind 股價資料（可選） |

---

## 專案結構

```
.
├── backend/
│   ├── app/
│   │   ├── crawlers/       # Yahoo 股市新聞爬蟲
│   │   ├── llm/            # Groq 客戶端、Few-shot prompt 設計
│   │   ├── rag/            # 嵌入向量、語意搜尋、多輪問答
│   │   ├── analysis/       # 情緒彙總、報酬對齊、回測
│   │   ├── services/       # API 資料服務層
│   │   └── db/             # 資料庫連線（SQLite 本地 / PostgreSQL 雲端）
│   ├── scripts/            # 自動化 pipeline 腳本
│   ├── requirements.txt            # 完整套件（本地開發）
│   ├── requirements-render.txt     # 精簡套件（Render 部署）
│   └── requirements-embeddings.txt # 含 sentence-transformers（GitHub Actions）
├── frontend/
│   ├── app/                # Next.js App Router、全域樣式
│   ├── components/         # Dashboard（Recharts 圖表、RAG 對話）
│   └── lib/                # API 型別定義、fetch 封裝
└── .github/workflows/
    └── daily_update.yml    # 每日自動化 pipeline
```

---

## Prompt 設計說明

### 新聞分析（Few-shot Prompting）

採用 7 個精心設計的標注範例，涵蓋：

- **正反例對比**：明確示範「台積電的新聞 target 應填 `2330` 而非 `半導體`」
- **五種新聞類型**：`stock / market / industry / macro / other`
- **信心分數準則**：0.9–1.0（訊號明確）→ 0.0–0.45（與台股關聯極弱）

### RAG 問答

- 系統提示要求先點出結論再補充細節（3–6 句），強制綜合多則新聞
- 輸出 JSON schema：`answer + citations + suggested_questions`
- 多輪對話注入最近 3 輪問答（最多 6 則訊息），控制 token 用量

### 每日摘要生成

- 輸入量化數據（情緒分數、偏多偏空標的、分析筆數）
- LLM 輸出自然語言敘述，`temperature=0.4` 增加語言多樣性
- Fallback：LLM 失敗時自動切換至模板文字，不中斷 pipeline

---

## 免責聲明

本系統所有分析結果**僅供學術研究與課程展示**，不構成任何投資建議。回測績效基於歷史資料，不代表未來表現。
