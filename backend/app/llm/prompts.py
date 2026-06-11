import json

from app.crawlers.yahoo_news import clean_news_content

PROMPT_VERSION = "twstock-news-v7"


def full_news_text(content: str) -> str:
    text = clean_news_content(content)
    if len(text) > 5000:
        text = f"{text[:2500]}\n[...]\n{text[-1500:]}"
    return text


# ---------------------------------------------------------------------------
# Few-shot examples embedded in the prompt
# ---------------------------------------------------------------------------
_FEW_SHOT = [
    # --- stock / positive ---
    {
        "title": "台積電EPS衝66.25元創新高 去年大賺1.7兆",
        "output": {
            "news_type": "stock", "target_type": "stock",
            "target": "2330", "target_name": "台積電",
            "targets": [{"target_type": "stock", "target": "2330", "target_name": "台積電",
                         "sentiment": "positive", "confidence": 1.0, "reason": "EPS創新高，獲利大幅成長"}],
            "sentiment": "positive", "confidence": 1.0, "reason": "EPS創新高，獲利大幅成長",
        },
    },
    # --- stock / negative ---
    {
        "title": "外資逢高調節392億元 連2賣 續砍台積電2.21萬張",
        "output": {
            "news_type": "stock", "target_type": "stock",
            "target": "2330", "target_name": "台積電",
            "targets": [{"target_type": "stock", "target": "2330", "target_name": "台積電",
                         "sentiment": "negative", "confidence": 0.85, "reason": "外資連續賣超，籌碼轉弱"}],
            "sentiment": "negative", "confidence": 0.85, "reason": "外資連續賣超，籌碼轉弱",
        },
    },
    # --- 關鍵反例：stock 類新聞 target 必須填代號，不能填產業詞 ---
    {
        "title": "AI發展速度超乎預期 魏哲家直言需求都流向台積電",
        "output": {
            "news_type": "stock", "target_type": "stock",
            "target": "2330", "target_name": "台積電",
            "targets": [{"target_type": "stock", "target": "2330", "target_name": "台積電",
                         "sentiment": "positive", "confidence": 0.9, "reason": "需求強勁，直接受益者為台積電"}],
            "sentiment": "positive", "confidence": 0.9, "reason": "需求強勁，直接受益者為台積電",
        },
        "wrong_example": {
            "target": "半導體",   # ❌ 標題明確指向台積電，不應填產業詞
        },
    },
    # --- market / negative ---
    {
        "title": "美股回檔衝擊！台股收盤重挫781點痛失4萬6大關",
        "output": {
            "news_type": "market", "target_type": "index",
            "target": "TAIEX", "target_name": "台灣加權指數",
            "targets": [{"target_type": "index", "target": "TAIEX", "target_name": "台灣加權指數",
                         "sentiment": "negative", "confidence": 1.0, "reason": "大盤重挫逾700點"}],
            "sentiment": "negative", "confidence": 1.0, "reason": "大盤重挫逾700點",
        },
    },
    # --- industry / positive ---
    {
        "title": "AI改寫景氣循環 全球半導體設備龍頭：產業正迎史上最強榮景",
        "output": {
            "news_type": "industry", "target_type": "industry",
            "target": "半導體", "target_name": "半導體產業",
            "targets": [{"target_type": "industry", "target": "半導體", "target_name": "半導體產業",
                         "sentiment": "positive", "confidence": 0.9, "reason": "整體產業景氣強勁"}],
            "sentiment": "positive", "confidence": 0.9, "reason": "整體產業景氣強勁",
        },
    },
    # --- 關鍵反例：無關台股的新聞 → other ---
    {
        "title": "梵蒂岡AI通諭下週一揭幕 教宗良十四世憂技術扭曲人性",
        "output": {
            "news_type": "other", "target_type": "other",
            "target": "", "target_name": "",
            "targets": [],
            "sentiment": "neutral", "confidence": 0.3, "reason": "與台股市場無直接關聯",
        },
    },
    # --- neutral：例行公告 ---
    {
        "title": "台積電代子公司 TSMC Global Ltd. 公告取得固定收益證券",
        "output": {
            "news_type": "stock", "target_type": "stock",
            "target": "2330", "target_name": "台積電",
            "targets": [{"target_type": "stock", "target": "2330", "target_name": "台積電",
                         "sentiment": "neutral", "confidence": 0.9, "reason": "例行財務公告，無明顯市場意義"}],
            "sentiment": "neutral", "confidence": 0.9, "reason": "例行財務公告，無明顯市場意義",
        },
    },
]


def build_news_analysis_messages(title: str, content: str) -> list[dict]:
    schema = {
        "news_type": "stock | etf | market | industry | macro | other",
        "target_type": "stock | etf | index | industry | commodity | macro | region | company_foreign | other",
        "target": "台灣股票代號（4-6位數字），或指數/產業關鍵字",
        "target_name": "繁體中文名稱，或空字串",
        "targets": [
            {
                "target_type": "...",
                "target": "...",
                "target_name": "...",
                "sentiment": "positive | neutral | negative",
                "confidence": "0.0–1.0",
                "reason": "繁體中文，不超過40字",
            }
        ],
        "sentiment": "positive | neutral | negative",
        "confidence": "0.0–1.0",
        "reason": "繁體中文，不超過40字",
    }

    few_shot_text = ""
    for i, ex in enumerate(_FEW_SHOT, 1):
        few_shot_text += f"\n範例 {i}：標題「{ex['title']}」\n"
        few_shot_text += f"正確輸出：{json.dumps(ex['output'], ensure_ascii=False)}\n"
        if "wrong_example" in ex:
            few_shot_text += (
                f"❌ 常見錯誤：target 填了「{ex['wrong_example']['target']}」"
                "——標題明確點名單一公司時，stock 類新聞的 target 必須是股票代號，不能是產業詞。\n"
            )

    rules = (
        "=== 分類規則 ===\n"
        "news_type 選擇依據：\n"
        "  stock    → 新聞主角是特定台股上市公司（含法人買賣超、個股漲跌、財報、公告）\n"
        "  etf      → 新聞主角是 ETF（0050、00878 等）\n"
        "  market   → 新聞主角是整體大盤、加權指數、或多國股市整體走勢\n"
        "  industry → 新聞主角是某一產業、技術趨勢或供應鏈（非特定公司）\n"
        "  macro    → 新聞主角是總經、利率、匯率、油價、Fed、政治事件\n"
        "  other    → 與台股市場無直接關聯\n\n"

        "=== target 填法（最重要規則）===\n"
        "【stock 類】target 必須是台灣股票代號（純數字，4-6 位），不可以是公司名稱或產業詞。\n"
        "  ✅ target=\"2330\"（台積電）  ✅ target=\"2454\"（聯發科）\n"
        "  ❌ target=\"台積電\"         ❌ target=\"半導體\"  ❌ target=\"AI晶片\"\n"
        "  若新聞標題或內文明確點名某公司但你不確定代號，填公司中文名稱也可以，但代號優先。\n\n"
        "【etf 類】target 填 ETF 代號，例如 0050、00878、00940。\n"
        "【market 類】target 填 TAIEX、NASDAQ、S&P500、道瓊等指數代稱。\n"
        "【industry 類】target 填產業關鍵字，例如「半導體」「AI伺服器」「PCB」「記憶體」。\n"
        "【macro 類】target 填「美元」「Fed利率」「油價」「美國通膨」等總經指標。\n"
        "【other 類】target 填空字串 \"\"。\n\n"

        "=== 情緒判斷 ===\n"
        "sentiment 是這則新聞對 target 的市場/投資意涵：\n"
        "  positive → 明確利多：營收創高、獲利大增、股價漲停、拿到大訂單、市場份額提升\n"
        "  negative → 明確利空：營收衰退、獲利下滑、法人賣超、失去訂單、股價下跌\n"
        "  neutral  → 例行公告、中性資訊、正負混雜、事件結果尚未明朗\n\n"

        "=== confidence 評分準則 ===\n"
        "  0.9–1.0 → 訊號非常明確（如年增+30%、漲跌停、EPS創新高）\n"
        "  0.7–0.85 → 方向明確，但有背景雜訊或間接因素\n"
        "  0.5–0.65 → 訊號模糊，正負各有，或消息來源不確定\n"
        "  0.0–0.45 → 非常不確定，或新聞與台股關聯極弱\n\n"

        "=== 多標的規則 ===\n"
        "若新聞同時提到多個明確標的（如「買超前十大」「族群齊漲」），\n"
        "targets 填 2-5 個最重要標的，target 填最主要的那一個。\n\n"

        "=== 其他 ===\n"
        "若新聞主角是外國公司（NVIDIA、Apple、AMD 等）且對台股無直接影響，\n"
        "news_type 填 other 或 macro，不要強套台股代號。\n"
        "請務必閱讀完整新聞內文，不可只看標題。\n"
        "只輸出合法 JSON，不加 markdown、不加解釋文字。\n"
    )

    return [
        {
            "role": "system",
            "content": (
                "你是一個台股財經新聞標註助理，專門判斷新聞的分類、影響標的、情緒方向與信心分數。"
                "請只輸出一個合法 JSON object，不要 markdown，不要輸出其他文字。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{rules}\n"
                f"=== 範例（請學習這些輸出格式）===\n"
                f"{few_shot_text}\n"
                f"=== Schema ===\n"
                f"{json.dumps(schema, ensure_ascii=False)}\n\n"
                f"=== 請分析以下新聞 ===\n"
                f"新聞標題：{title}\n\n"
                f"新聞全文：\n{full_news_text(content)}"
            ),
        },
    ]
