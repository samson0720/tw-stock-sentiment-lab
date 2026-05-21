# Data Pipeline

## Step 1: 初始化資料庫

```powershell
cd backend
python scripts/init_db.py
```

## Step 2: 爬取新聞

```powershell
python scripts/fetch_news.py --limit 100
```

輸出：

- `raw_news`
- `outputs/tables/raw_news.csv`

## Step 3: LLM 分析新聞

```powershell
python scripts/analyze_news_with_llm.py --limit 100 --model qwen2.5:7b
```

輸出：

- `llm_news_analysis`
- `outputs/tables/llm_news_analysis.csv`

若 Ollama 無法連線，預設會使用規則型 fallback，方便 pipeline 繼續跑完，但正式報告應標明模型來源。

## Step 4: 抓取股價

```powershell
python scripts/fetch_prices.py --stock-ids 2330,0050 --start-date 2024-01-01
```

輸出：

- `stock_prices`
- `outputs/tables/stock_prices.csv`

## Step 5: 對齊新聞與未來報酬

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

## Step 6: 建立日度情緒

```powershell
python scripts/build_daily_sentiment.py
```

輸出：

- `daily_sentiment`
- `outputs/tables/daily_sentiment.csv`

## Step 7: 回測

```powershell
python scripts/run_backtest.py
```

輸出：

- `backtest_results`
- `outputs/tables/backtest_equity_curve.csv`
- `outputs/tables/backtest_metrics.csv`
