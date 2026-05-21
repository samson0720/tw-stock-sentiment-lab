import re


COMMON_STOCK_NAMES = {
    "台積電": "2330",
    "聯發科": "2454",
    "鴻海": "2317",
    "廣達": "2382",
    "緯創": "3231",
    "台達電": "2308",
    "長榮": "2603",
    "陽明": "2609",
    "萬海": "2615",
    "富邦金": "2881",
    "國泰金": "2882",
    "0050": "0050",
}

MARKET_TARGETS = {"TAIEX", "TAIEX/0050", "加權指數", "台股", "大盤", "櫃買", "0050"}


def normalize_target(news_type: str | None, target: str | None) -> str | None:
    if not target:
        return "0050" if news_type == "market" else None
    value = str(target).strip().upper()
    if news_type == "market":
        return "0050" if value in MARKET_TARGETS or "0050" in value else value
    match = re.search(r"\b\d{4}\b", value)
    if match:
        return match.group(0)
    for name, stock_id in COMMON_STOCK_NAMES.items():
        if name.upper() in value:
            return stock_id
    return value
