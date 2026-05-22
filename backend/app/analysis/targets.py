import re


COMMON_STOCK_NAMES = {
    "TSMC": "2330",
    "台積電": "2330",
    "台積": "2330",
    "Tai積電": "2330",
    "鴻海": "2317",
    "HON HAI": "2317",
    "聯發科": "2454",
    "MEDIATEK": "2454",
    "聯電": "2303",
    "UMC": "2303",
    "群創": "3481",
    "INNOLUX": "3481",
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

MARKET_TARGETS = {
    "TAIEX",
    "TAIEX/0050",
    "台股大盤",
    "台股",
    "加權指數",
    "大盤",
    "櫃買",
    "0050",
}
MARKET_TERMS = ("TAIEX", "加權指數", "台股大盤", "台股", "大盤", "櫃買")


def _normalize_text(value: str) -> str:
    return (
        value.strip()
        .replace("（", "(")
        .replace("）", ")")
        .replace("－", "-")
        .replace("，", ",")
    )


def _extract_stock_id(value: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{4})(?:\s*(?:\.|-)?\s*(?:TW|TWO))?(?!\d)", value, flags=re.IGNORECASE)
    return match.group(1) if match else None


def normalize_target(news_type: str | None, target: str | None) -> str | None:
    if not target:
        return "0050" if news_type == "market" else None
    raw_value = _normalize_text(str(target))
    value = raw_value.upper()

    if value in MARKET_TARGETS or any(term in value for term in MARKET_TERMS):
        return "0050"

    stock_id = _extract_stock_id(value)
    if stock_id:
        return stock_id

    for name, stock_id in COMMON_STOCK_NAMES.items():
        if name.upper() in value or name in raw_value:
            return stock_id

    return "0050" if news_type == "market" and "0050" in value else value
