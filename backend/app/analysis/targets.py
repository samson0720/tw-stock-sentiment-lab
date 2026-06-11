import re


STOCK_UNIVERSE = {
    "0050": {"0050", "元大台灣50"},
    "1234": {"王品"},
    "1303": {"南亞", "南亞塑膠"},
    "1722": {"台肥", "臺灣肥料"},
    "1802": {"台玻", "台灣玻璃"},
    "2002": {"中鋼", "中國鋼鐵"},
    "2303": {"聯電", "UMC", "聯華電子"},
    "2308": {"台達電", "DELTA"},
    "2312": {"金寶", "金寶電"},
    "2313": {"華通"},
    "2317": {"鴻海", "HON HAI"},
    "2327": {"國巨", "國巨電子"},
    "2330": {"台積電", "台積", "TSMC", "Tai積電"},
    "2337": {"旺宏"},
    "2344": {"華邦電", "Winbond"},
    "2347": {"聯強"},
    "2354": {"鴻勁"},
    "2382": {"廣達"},
    "2408": {"南亞科", "南亞科技"},
    "2454": {"聯發科", "MEDIATEK"},
    "2504": {"國產"},
    "2603": {"長榮"},
    "2609": {"陽明"},
    "2610": {"華航", "中華航空"},
    "2615": {"萬海"},
    "2731": {"雄獅"},
    "2881": {"富邦金"},
    "2882": {"國泰金"},
    "3017": {"奇鋐"},
    "3037": {"欣興", "欣興電子"},
    "3131": {"弘塑", "弘塑科技", "GPTC"},
    "3231": {"緯創"},
    "3416": {"融程電"},
    "3481": {"群創", "INNOLUX"},
    "3711": {"日月光投控", "日月光", "ASE"},
    "4919": {"新唐"},
    "4958": {"臻鼎", "臻鼎-KY"},
    "5269": {"祥碩"},
    "6116": {"嘉晶"},
    "6139": {"亞翔"},
    "6584": {"南俊國際", "南俊"},
    "6617": {"共信-KY", "共信"},
    "6669": {"緯穎"},
    "9914": {"築間"},
}

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

for _stock_id, _names in STOCK_UNIVERSE.items():
    for _name in _names:
        COMMON_STOCK_NAMES.setdefault(_name, _stock_id)

FOREIGN_COMPANIES = {
    "AMD": ("AMD", "AMD", "超微"),
    "NVIDIA": ("NVIDIA", "NVDA", "輝達", "英偉達"),
    "APPLE": ("Apple", "AAPL", "蘋果"),
    "INTEL": ("Intel", "INTC", "英特爾"),
    "SPOTIFY": ("Spotify", "SPOT"),
    "VOLVO": ("Volvo",),
    "QUANTINUUM": ("Quantinuum",),
    "OPENROUTER": ("OpenRouter",),
    "OKLO": ("Oklo",),
    "SUPERMICRO": ("美超微", "SMCI", "SUPER MICRO"),
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


def _match_key(value: str) -> str:
    return re.sub(r"[\s,，()（）股份有限公司科技]+", "", _normalize_text(value).upper())


def _extract_stock_id(value: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{4})(?:\s*(?:\.|-)?\s*(?:TW|TWO))?(?!\d)", value, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _foreign_company(value: str) -> str | None:
    key = _match_key(value)
    if not key:
        return None
    matches: list[tuple[int, str]] = []
    for canonical, aliases in FOREIGN_COMPANIES.items():
        for alias in aliases:
            alias_key = _match_key(alias)
            if alias_key and alias_key in key:
                matches.append((len(alias_key), canonical))
    if not matches:
        return None
    return max(matches)[1]


def _stock_id_for_company_name(value: str) -> str | None:
    key = _match_key(value)
    if not key:
        return None
    matches: list[tuple[int, str]] = []
    for stock_id, names in STOCK_UNIVERSE.items():
        for name in names:
            name_key = _match_key(name)
            if name_key and name_key in key:
                matches.append((len(name_key), stock_id))
    if not matches:
        return None
    return max(matches)[1]


def _stock_name_matches(stock_id: str, value: str) -> bool:
    names = STOCK_UNIVERSE.get(stock_id)
    return not names or _stock_id_for_company_name(value) == stock_id


def _preferred_stock_name(stock_id: str, fallback: str = "") -> str:
    names = STOCK_UNIVERSE.get(stock_id) or set()
    if fallback and any(_match_key(fallback) == _match_key(name) for name in names):
        return fallback
    return sorted(names, key=len, reverse=True)[0] if names else fallback


def normalize_target_record(
    target_type: str | None,
    target: str | None,
    target_name: str | None = None,
) -> tuple[str, str | None, str]:
    normalized_type = str(target_type or "other").lower().strip()
    raw_target = _normalize_text(str(target or "").strip())
    raw_name = _normalize_text(str(target_name or "").strip())
    combined = " ".join(part for part in (raw_target, raw_name) if part)

    foreign = _foreign_company(combined)
    if foreign:
        return "company_foreign", foreign, raw_name or foreign

    stock_id = _extract_stock_id(raw_target.upper()) if raw_target else None
    name_stock_id = _stock_id_for_company_name(raw_name) or _stock_id_for_company_name(raw_target)
    if stock_id:
        if raw_name and name_stock_id and name_stock_id != stock_id:
            return "stock", name_stock_id, _preferred_stock_name(name_stock_id, raw_name)
        if raw_name and not _stock_name_matches(stock_id, raw_name):
            return "other", raw_name, raw_name
        return "stock", stock_id, _preferred_stock_name(stock_id, raw_name)

    if name_stock_id:
        return "stock", name_stock_id, _preferred_stock_name(name_stock_id, raw_name or raw_target)

    if normalized_type == "stock" and raw_target:
        return "company_foreign", raw_target, raw_name
    return normalized_type, raw_target or None, raw_name


def normalize_target(news_type: str | None, target: str | None, target_name: str | None = None) -> str | None:
    if not target:
        return "0050" if news_type == "market" else None
    raw_value = _normalize_text(str(target))
    value = raw_value.upper()

    if value in MARKET_TARGETS or any(term in value for term in MARKET_TERMS):
        return "0050"

    normalized_type, normalized_target, _ = normalize_target_record(news_type, raw_value, target_name)
    if normalized_type == "company_foreign":
        return normalized_target
    if normalized_target:
        return normalized_target

    return "0050" if news_type == "market" and "0050" in value else value
