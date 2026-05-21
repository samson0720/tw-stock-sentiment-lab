# Pipeline Status

Generated at: 2026-05-18

## Summary

100-news offline pipeline test completed. FastAPI and frontend do not call Groq; LLM analysis is still handled only by `backend/scripts/analyze_news_with_llm.py`.

## Table Counts

| Table | Rows |
|---|---:|
| raw_news | 150 |
| llm_news_analysis | 100 |
| stock_prices | 1,641 |
| aligned_news_returns | 49 |
| daily_sentiment | 2 |
| backtest_results | 0 |

## Raw News Quality

| Check | Count |
|---|---:|
| Empty title | 0 |
| Empty content | 0 |
| Empty published_at | 0 |
| Duplicate URL groups | 0 |
| Duplicate title groups | 0 |

Yahoo crawler now combines RSS, the main Yahoo stock news page, and quote news pages for 0050, 2330, 2317, 2454, and 2303.

## LLM Analysis

| Metric | Count |
|---|---:|
| Total analyzed | 100 |
| Success | 100 |
| Failed | 0 |
| JSON parse failed | 0 |
| Success rate | 100.0% |

### News Type Distribution

| news_type | Count |
|---|---:|
| industry | 41 |
| market | 35 |
| stock | 24 |

### Sentiment Distribution

| sentiment | Count |
|---|---:|
| neutral | 45 |
| negative | 32 |
| positive | 23 |

### Failed Cases

No LLM failed cases in this run.

## Validation Export

Manual validation sample exported:

```text
outputs/tables/validation_sample.csv
```

Rows exported: 100

## Price Data

FinMind failed in this Windows/Python environment with `asyncio.unix_events`. yfinance also returned empty data because Yahoo Finance cookie/timezone lookup failed. The script fell back to the direct Yahoo Finance chart API and stored usable daily prices.

| stock_id | Source | Start Date | End Date | Rows |
|---|---|---:|---:|---:|
| 0050 | YahooChart | 2025-01-02 | 2026-05-18 | 329 |
| 2303 | YahooChart | 2025-01-02 | 2026-05-18 | 328 |
| 2317 | YahooChart | 2025-01-02 | 2026-05-18 | 328 |
| 2330 | YahooChart | 2025-01-02 | 2026-05-18 | 328 |
| 2454 | YahooChart | 2025-01-02 | 2026-05-18 | 328 |

## Alignment Results

| Target | Aligned News Rows |
|---|---:|
| 0050 | 33 |
| 2330 | 16 |

Total `aligned_news_returns` rows: 49

Current future return null counts:

| Field | Null Count |
|---|---:|
| future_return_1d | 49 |
| future_return_3d | 49 |
| future_return_5d | 49 |

Reason: the analyzed Yahoo news sample is concentrated on 2026-05-18, which is the latest available trading date in the downloaded price data. There is no next trading day yet, so future return fields are correctly left null instead of fabricating future prices.

## Daily Sentiment

| Target | Start Date | End Date | Rows | News Count |
|---|---:|---:|---:|---:|
| 0050 | 2026-05-18 | 2026-05-18 | 1 | 33 |
| 2330 | 2026-05-18 | 2026-05-18 | 1 | 16 |

Total `daily_sentiment` rows: 2

## Next Steps

1. Collect older news samples so `future_return_1d`, `future_return_3d`, and `future_return_5d` can be populated without look-ahead bias.
2. Ask teammates to fill `outputs/tables/validation_sample.csv` for manual LLM validation.
3. Expand target normalization for common company names and ETF tickers found in the first 100-news run.
4. After older aligned samples exist, run statistical notebooks and then backtest.
5. Keep dashboard work paused until the analysis tables contain enough non-null return observations.
