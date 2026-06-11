# Pipeline Status

Generated at: 2026-05-26

## Summary

Historical data refresh focused on making future returns non-null for downstream notebooks and backtests.
FastAPI and frontend do not call Groq; LLM analysis remains limited to `backend/scripts/analyze_news_with_llm.py`.

## Table Counts

| Table | Rows |
|---|---:|
| raw_news | 726 |
| llm_news_analysis total | 561 |
| llm_news_analysis success | 523 |
| llm_news_analysis failed | 38 |
| llm_news_analysis pending | 165 |
| stock_prices | 2,687 |
| aligned_news_returns | 280 |
| daily_sentiment | 45 |
| human_validation | 0 |
| backtest_results | 1 |

## Historical News Target

| Requirement | Current | Status |
|---|---:|---|
| Valid news from 2026-03-01 to 2026-05-08 | 437 | OK |

## LLM News Type Distribution

| Value | Rows |
|---|---:|
| market | 225 |
| industry | 180 |
| stock | 86 |
| NULL | 38 |
| other | 20 |
| macro | 12 |

## LLM Sentiment Distribution

| Value | Rows |
|---|---:|
| neutral | 230 |
| positive | 191 |
| negative | 102 |
| NULL | 38 |

## LLM Target Distribution Top 40

| Value | Rows |
|---|---:|
| market / 0050 | 74 |
| market / TAIEX | 63 |
| market / TAIEX/0050 | 58 |
| stock / 2330 | 24 |
| industry / NULL | 22 |
| other / NULL | 20 |
| industry / 半導體 | 13 |
| industry / AI | 11 |
| industry / 台積電 | 10 |
| industry / AI晶片 | 8 |
| industry / TSMC Global Ltd. | 8 |
| industry / NVIDIA | 6 |
| stock / 2454 | 6 |
| industry / ETF | 5 |
| market / 2330 | 5 |
| stock / 2303 | 5 |
| industry / 半導體產業 | 4 |
| stock / 00403A | 4 |
| industry / 00981A | 3 |
| macro / 美國 | 3 |
| stock / 2327 | 3 |
| industry / 2330.TW | 2 |
| industry / Arm | 2 |
| industry / TSMC | 2 |
| industry / semiconductor | 2 |
| industry / semiconductor industry | 2 |
| industry / 台積電(2330) | 2 |
| macro / 台灣 | 2 |
| market / TAIEX/40769.29 | 2 |
| market / TAIEX/41138.85 | 2 |
| market / 台積電 | 2 |
| market / 黃金 | 2 |
| stock / 00878 | 2 |
| stock / 2330-TW | 2 |
| stock / 2408 | 2 |
| stock / 4958 | 2 |
| industry / 00991A | 1 |
| industry / 2303.TW | 1 |
| industry / 2330 | 1 |
| industry / 2330-TW | 1 |

## Future Return Coverage

| Field | Non-null Rows | Non-null Ratio |
|---|---:|---:|
| future_return_1d | 280 | 100.0% |
| future_return_3d | 280 | 100.0% |
| future_return_5d | 227 | 81.1% |

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
| 0050 | 2026-04-29 | 2026-05-18 | 11 | 178 |
| 2059 | 2026-05-07 | 2026-05-07 | 1 | 1 |
| 2303 | 2026-04-30 | 2026-05-08 | 5 | 9 |
| 2327 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2330 | 2026-04-29 | 2026-05-18 | 8 | 68 |
| 2347 | 2026-05-05 | 2026-05-05 | 1 | 1 |
| 2382 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2408 | 2026-05-06 | 2026-05-06 | 1 | 1 |
| 2454 | 2026-05-04 | 2026-05-08 | 5 | 9 |
| 2504 | 2026-05-18 | 2026-05-18 | 1 | 1 |
| 2547 | 2026-04-29 | 2026-04-29 | 1 | 1 |
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
