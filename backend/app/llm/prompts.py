import json


PROMPT_VERSION = "twstock-news-v6"

CONTENT_CUTOFF_MARKERS = ("廣告", "更多FTNN", "更多新聞", "檢視留言", "熱門留言", "相關內容")


def full_news_text(content: str) -> str:
    text = "\n".join(line.strip() for line in content.splitlines() if line.strip())
    marker_positions = [text.find(marker) for marker in CONTENT_CUTOFF_MARKERS if marker in text]
    if marker_positions:
        text = text[: min(marker_positions)].strip()
    if len(text) > 5000:
        text = f"{text[:2500]}\n[...]\n{text[-1500:]}"
    return text


def build_news_analysis_messages(title: str, content: str) -> list[dict]:
    schema = {
        "news_type": "stock | etf | market | industry | macro | other",
        "target_type": "stock | etf | index | industry | commodity | macro | region | company_foreign | other",
        "target": "main target explicitly mentioned in the news",
        "target_name": "Traditional Chinese target name, or empty string",
        "targets": [
            {
                "target_type": "stock | etf | index | industry | commodity | macro | region | company_foreign | other",
                "target": "target id/name explicitly mentioned in the news",
                "target_name": "Traditional Chinese target name, or empty string",
                "sentiment": "positive | neutral | negative",
                "confidence": "number from 0 to 1",
                "reason": "Traditional Chinese sentence, no more than 40 characters",
            }
        ],
        "sentiment": "positive | neutral | negative",
        "confidence": "number from 0 to 1",
        "reason": "Traditional Chinese sentence, no more than 40 characters",
    }
    return [
        {
            "role": "system",
            "content": (
                "你是一個台股與財經新聞標註助理。請根據新聞標題與新聞全文，"
                "判斷這則新聞的分類、主要影響標的、情緒方向與信心分數。"
                "請務必閱讀完整新聞內容，不可以只根據標題或前幾段判斷。"
                "請只輸出一個合法 JSON object，不要 markdown，不要輸出其他文字。"
            ),
        },
        {
            "role": "user",
            "content": (
                "重要規則：\n"
                "1. 不要猜測新聞中沒有明確出現的股票代號、公司名稱、ETF 或指數。\n"
                "2. 如果新聞主角不是台股公司，不可以硬套成 2330、台積電、0050、TAIEX 或台股。\n"
                "3. target 必須是新聞最主要影響的對象，而不是文章中隨便提到的相關詞。\n"
                "4. 如果新聞明確提到個股，target 優先填股票代號；如果沒有代號，填公司名稱。\n"
                "5. 如果新聞是 ETF，target 填 ETF 代號。\n"
                "6. 如果新聞是大盤或市場新聞，target 填指數、市場、國家或商品，例如 TAIEX、KOSPI、NASDAQ、油價、美元。\n"
                "7. 如果新聞是產業趨勢，target 填具體產業或技術主題，例如 AI晶片、半導體、旅遊業、記憶體。\n"
                "8. sentiment 是判斷這則新聞對 target 的投資或市場意義。\n"
                "9. 若正負訊號混雜、只是公告、或資訊不足，sentiment 請選 neutral。\n"
                "10. reason 請簡短說明，不要超過 40 字。\n"
                "11. 若新聞重點是外資、投信、自營商買超/賣超/倒貨某檔或少數幾檔股票，news_type 應為 stock。\n"
                "12. 若標題或全文主角是單一公司，target 應填該公司代號；沒有明確代號才填公司名稱。\n"
                "13. market 只用於大盤、整體市場、國家股市或指數新聞，不可用於單一產業或單一公司。\n"
                "14. news_type 與 target_type 必須一致；target_type=industry 時，news_type 通常應為 industry。\n"
                "15. 若新聞同時明確影響多個標的，targets 必須列出多個標的；target 保留最主要標的。\n"
                "16. 地區、國家、區域市場請用 target_type=region，例如台灣、美國、東南亞、歐洲。\n\n"
                "17. 如果新聞標題或正文明確提到「這幾檔」、「多檔」、「族群」、「概念股」、"
                "「買超前十大」、「賣超前十大」，targets 請列出 2 到 5 個最重要標的。\n"
                "18. 主 target 仍選擇新聞最主要聚焦的標的；若標題特別點名某一家公司，主 target 選該公司。\n"
                "19. 個股 target 一律優先輸出股票代號；target_name 才放公司名稱，例如 target=\"2313\", target_name=\"華通\"。\n"
                "20. 不要只因為其中一家公司金額最大，就忽略正文中明確列為主角的其他標的。\n\n"
                "news_type 只能是：stock、etf、market、industry、macro、other\n"
                "target_type 只能是：stock、etf、index、industry、commodity、macro、region、company_foreign、other\n"
                "sentiment 只能是：positive、neutral、negative\n\n"
                f"Schema: {json.dumps(schema, ensure_ascii=False)}\n\n"
                "JSON 格式：\n"
                "{\n"
                '  "news_type": "",\n'
                '  "target_type": "",\n'
                '  "target": "",\n'
                '  "target_name": "",\n'
                '  "targets": [],\n'
                '  "sentiment": "",\n'
                '  "confidence": 0.0,\n'
                '  "reason": ""\n'
                "}\n\n"
                f"新聞標題：\n{title}\n\n"
                f"新聞全文：\n{full_news_text(content)}"
            ),
        },
    ]
