# 模型驗證設計

## 目的

LLM 分析結果不能直接視為真實標籤。本專案需要抽樣人工標註，檢查新聞類型、標的與情緒方向是否合理。

## 建立抽樣檔

```powershell
cd backend
python scripts/create_validation_sample.py --sample-size 100
```

輸出：

- `outputs/tables/human_validation_sample.csv`

## 人工標註欄位

- `human_news_type`
- `human_target`
- `human_sentiment`
- `note`

## 報告輸出

- 新聞類型判斷準確率
- 情緒判斷準確率
- 常見誤判類型
- 5 到 10 個誤判案例

## 注意

若正式分析曾使用規則型 fallback，需在報告中清楚揭露，不能將 fallback 結果誤稱為 LLM 結果。
