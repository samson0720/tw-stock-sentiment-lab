# Pipeline Status

Generated at: 2026-05-22

## Summary

Historical data refresh focused on making future returns non-null for downstream notebooks and backtests.
FastAPI and frontend do not call Groq; LLM analysis remains limited to `backend/scripts/analyze_news_with_llm.py`.

## Table Counts

| Table | Rows |
|---|---:|
| raw_news | 570 |
| llm_news_analysis total | 426 |
| llm_news_analysis success | 426 |
| llm_news_analysis failed | 0 |
| llm_news_analysis pending | 144 |
| stock_prices | 2,687 |
| aligned_news_returns | 304 |
| daily_sentiment | 46 |
| human_validation | 0 |
| backtest_results | 0 |

## Historical News Target

| Requirement | Current | Status |
|---|---:|---|
| Valid news from 2026-03-01 to 2026-05-08 | 437 | OK |

## LLM News Type Distribution

| Value | Rows |
|---|---:|
| market | 201 |
| industry | 136 |
| stock | 88 |
| ignore | 1 |

## LLM Sentiment Distribution

| Value | Rows |
|---|---:|
| neutral | 171 |
| positive | 166 |
| negative | 89 |

## LLM Target Distribution Top 40

| Value | Rows |
|---|---:|
| market / 0050 | 62 |
| market / TAIEX/0050 | 58 |
| market / TAIEX | 53 |
| stock / 2330 | 43 |
| industry / NULL | 14 |
| industry / 台積電 | 10 |
| industry / TSMC Global Ltd. | 8 |
| industry / 半導體 | 7 |
| stock / 2454 | 6 |
| industry / AI | 5 |
| industry / ETF | 5 |
| market / 2330 | 5 |
| stock / 2303 | 5 |
| industry / 半導體產業 | 4 |
| industry / 記憶體 | 3 |
| stock / 00403A | 3 |
| industry / 00981A | 2 |
| industry / 2330.TW | 2 |
| industry / Arm | 2 |
| industry / TSMC | 2 |
| industry / semiconductor | 2 |
| industry / semiconductor industry | 2 |
| industry / 台積電(2330) | 2 |
| market / TAIEX/40769.29 | 2 |
| market / TAIEX/41138.85 | 2 |
| market / 台積電 | 2 |
| market / 黃金 | 2 |
| stock / 00878 | 2 |
| stock / 2330-TW | 2 |
| ignore / NULL | 1 |
| industry / 00991A | 1 |
| industry / 2303.TW | 1 |
| industry / 2330 | 1 |
| industry / 2330-TW | 1 |
| industry / 2731 | 1 |
| industry / 3498.TWO | 1 |
| industry / 5269 | 1 |
| industry / 7744 | 1 |
| industry / ABF載板 | 1 |
| industry / AI晶片競爭 | 1 |

## Future Return Coverage

| Field | Non-null Rows | Non-null Ratio |
|---|---:|---:|
| future_return_1d | 304 | 100.0% |
| future_return_3d | 304 | 100.0% |
| future_return_5d | 231 | 76.0% |

## Price Data

| stock_id | Start Date | End Date | Rows |
|---|---:|---:|---:|
| 0050 | 2025-01-02 | 2026-05-22 | 333 |
| 2059 | 2026-03-02 | 2026-05-22 | 57 |
| 2303 | 2025-01-02 | 2026-05-22 | 332 |
| 2317 | 2025-01-02 | 2026-05-22 | 332 |
| 2327 | 2026-03-02 | 2026-05-22 | 57 |
| 2330 | 2025-01-02 | 2026-05-22 | 332 |
| 2347 | 2026-03-02 | 2026-05-22 | 57 |
| 2382 | 2026-03-02 | 2026-05-22 | 57 |
| 2408 | 2026-03-02 | 2026-05-22 | 57 |
| 2454 | 2025-01-02 | 2026-05-22 | 332 |
| 2504 | 2026-03-02 | 2026-05-22 | 57 |
| 2547 | 2026-03-02 | 2026-05-22 | 57 |
| 2609 | 2026-03-02 | 2026-05-22 | 57 |
| 2731 | 2026-03-02 | 2026-05-22 | 57 |
| 3037 | 2026-03-02 | 2026-05-22 | 57 |
| 3060 | 2026-03-02 | 2026-05-22 | 57 |
| 3481 | 2026-03-02 | 2026-05-22 | 57 |
| 3711 | 2026-03-02 | 2026-05-22 | 57 |
| 5269 | 2026-03-02 | 2026-05-22 | 57 |
| 6184 | 2026-03-02 | 2026-05-22 | 57 |
| 6451 | 2026-03-02 | 2026-05-22 | 57 |
| 7769 | 2026-03-02 | 2026-05-22 | 57 |
| 8261 | 2026-03-02 | 2026-05-22 | 57 |

## Daily Sentiment

| Target | Start Date | End Date | Rows | News Count |
|---|---:|---:|---:|---:|
| 0050 | 2026-04-29 | 2026-05-18 | 11 | 181 |
| 2059 | 2026-05-07 | 2026-05-07 | 1 | 1 |
| 2303 | 2026-04-30 | 2026-05-08 | 5 | 9 |
| 2327 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2330 | 2026-04-29 | 2026-05-18 | 8 | 88 |
| 2347 | 2026-05-05 | 2026-05-05 | 1 | 1 |
| 2382 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2408 | 2026-05-06 | 2026-05-06 | 1 | 1 |
| 2454 | 2026-05-04 | 2026-05-08 | 5 | 9 |
| 2504 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2547 | 2026-04-29 | 2026-04-29 | 1 | 1 |
| 2609 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2731 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 3037 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 3060 | 2026-05-07 | 2026-05-07 | 1 | 1 |
| 3711 | 2026-04-30 | 2026-04-30 | 1 | 1 |
| 5269 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 6184 | 2026-05-07 | 2026-05-07 | 1 | 1 |
| 6451 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 7769 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 8261 | 2026-05-18 | 2026-05-18 | 1 | 1 |

## Notebook Readiness

Ready for notebook analysis: yes

Criteria used here: at least 300 valid historical news rows in the target window and at least 100 rows with non-null 5-day future returns.

## Next Steps

1. Run statistical notebooks and inspect whether signal strength is meaningful before backtesting.
