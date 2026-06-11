from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


YAHOO_RSS_URL = "https://tw.stock.yahoo.com/rss"
YAHOO_NEWS_URL = "https://tw.stock.yahoo.com/news"
YAHOO_NEWS_SEARCH_URL = "https://tw.news.yahoo.com/search"
YAHOO_FINANCE_STREAM_API = "https://tw-gw-news.media.yahoo.com/api/v1/gql/saved_query"
QUOTE_NEWS_URLS = [
    "https://tw.stock.yahoo.com/quote/0050.TW/news",
    "https://tw.stock.yahoo.com/quote/2330.TW/news",
    "https://tw.stock.yahoo.com/quote/2317.TW/news",
    "https://tw.stock.yahoo.com/quote/2454.TW/news",
    "https://tw.stock.yahoo.com/quote/2303.TW/news",
    "https://tw.stock.yahoo.com/quote/2308.TW/news",
    "https://tw.stock.yahoo.com/quote/2382.TW/news",
    "https://tw.stock.yahoo.com/quote/2344.TW/news",
    "https://tw.stock.yahoo.com/quote/2327.TW/news",
    "https://tw.stock.yahoo.com/quote/3711.TW/news",
    "https://tw.stock.yahoo.com/quote/3037.TW/news",
    "https://tw.stock.yahoo.com/quote/2337.TW/news",
    "https://tw.stock.yahoo.com/quote/2408.TW/news",
    "https://tw.stock.yahoo.com/quote/3231.TW/news",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 twstock-sentiment-research/0.1",
    "Referer": "https://tw.news.yahoo.com/finance/archive/",
}
CONTENT_CUTOFF_MARKERS = (
    "廣告",
    "更多FTNN",
    "更多新聞",
    "檢視留言",
    "熱門留言",
    "相關內容",
    "延伸閱讀",
    "推薦閱讀",
    "看更多",
    "更多文章",
    "Yahoo奇摩股市",
)
CONTENT_DROP_PATTERNS = (
    r"^\s*Yahoo奇摩股市.*$",
    r"^\s*更多新聞.*$",
    r"^\s*延伸閱讀.*$",
    r"^\s*推薦閱讀.*$",
    r"^\s*相關內容.*$",
    r"^\s*熱門留言.*$",
    r"^\s*檢視留言.*$",
)
DEFAULT_HISTORICAL_SEARCH_TERMS = [
    "台股",
    "台股 0050",
    "大盤 加權指數",
    "ETF 0050",
    "台積電 2330",
    "鴻海 2317",
    "聯發科 2454",
    "聯電 2303",
    "半導體 台股",
    "AI 台股 台積電",
    "廣達 2382",
    "日月光 3711",
    "欣興 3037",
    "南亞科 2408",
    "台達電 2308",
]
DEFAULT_FINANCE_API_KEYWORDS = ["2330", "0050", "2317", "2454", "2303", "TAIEX", "ETF", "2308", "2382", "2344", "2327", "3711", "3037", "2408"]


@dataclass
class NewsItem:
    title: str
    content: str
    source: str
    published_at: str | None
    url: str
    crawled_at: str


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_news_content(content: str) -> str:
    text = "\n".join(line.strip() for line in (content or "").splitlines() if line.strip())
    if not text:
        return ""
    marker_positions = [text.find(marker) for marker in CONTENT_CUTOFF_MARKERS if marker in text]
    if marker_positions:
        text = text[: min(marker_positions)]
    for pattern in CONTENT_DROP_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)
    return clean_text(text)


def parse_rss_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def parse_any_datetime(value: str | None) -> str | None:
    if not value:
        return None
    rss_value = parse_rss_datetime(value)
    if rss_value:
        return rss_value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat(timespec="seconds")
    except ValueError:
        return clean_text(str(value)) or None


def parse_datetime_date(value: str | None) -> date | None:
    parsed = parse_any_datetime(value)
    if not parsed:
        return None
    try:
        return datetime.fromisoformat(parsed.replace("Z", "+00:00")).date()
    except ValueError:
        match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", parsed)
        if not match:
            return None
        year, month, day = (int(part) for part in match.groups())
        return date(year, month, day)


def parse_article_datetime(soup: BeautifulSoup) -> str | None:
    for attrs in (
        {"property": "article:published_time"},
        {"name": "pubdate"},
        {"name": "publishdate"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content"):
            return str(meta["content"])
    time_tag = soup.find("time")
    if time_tag:
        value = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        return parse_any_datetime(value)
    return None


def fetch_article_content(url: str, timeout: int = 15) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return extract_article_content(soup)


def extract_article_content(soup: BeautifulSoup) -> str:
    candidates: list[str] = []
    for selector in ["article", "[data-test-locator='content']", ".caas-body", "main"]:
        node = soup.select_one(selector)
        if node:
            candidates.append(node.get_text(" ", strip=True))
    if not candidates:
        candidates.append(" ".join(p.get_text(" ", strip=True) for p in soup.find_all("p")))
    return clean_news_content(max(candidates, key=len, default=""))


def fetch_article(url: str, timeout: int = 20) -> NewsItem | None:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title_node = soup.find("h1")
    title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        meta_title = soup.find("meta", attrs={"property": "og:title"})
        title = clean_text(str(meta_title.get("content", ""))) if meta_title else ""
    content = extract_article_content(soup)
    published_at = parse_article_datetime(soup)
    if not title or not content or not published_at:
        return None
    return NewsItem(
        title=title,
        content=content,
        source="Yahoo Stock News" if urlparse(url).netloc == "tw.stock.yahoo.com" else "Yahoo News",
        published_at=published_at,
        url=url,
        crawled_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def normalize_news_url(href: str) -> str | None:
    url = urljoin("https://tw.stock.yahoo.com", href).split("?")[0]
    parsed = urlparse(url)
    if parsed.netloc not in {"tw.stock.yahoo.com", "tw.news.yahoo.com"}:
        return None
    if parsed.netloc == "tw.stock.yahoo.com" and (
        not parsed.path.startswith("/news/") or parsed.path == "/news/"
    ):
        return None
    if not parsed.path.endswith(".html"):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def discover_page_urls(limit: int = 120) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for page_url in [YAHOO_NEWS_URL, *QUOTE_NEWS_URLS]:
        response = requests.get(page_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            url = normalize_news_url(str(link["href"]))
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= limit:
                return urls
    return urls


def discover_search_urls(terms: list[str], start_date: date, end_date: date, limit: int) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    months = sorted({(start_date.year, start_date.month), (end_date.year, end_date.month)})
    for year in range(start_date.year, end_date.year + 1):
        month_start = start_date.month if year == start_date.year else 1
        month_end = end_date.month if year == end_date.year else 12
        for month in range(month_start, month_end + 1):
            months.append((year, month))

    month_terms = [f"{year}-{month:02d}" for year, month in sorted(set(months))]
    queries: list[str] = []
    for term in terms:
        queries.append(term)
        for month_term in month_terms:
            queries.append(f"{term} {month_term}")

    for query in queries:
        if len(urls) >= limit:
            break
        search_url = f"{YAHOO_NEWS_SEARCH_URL}?p={quote_plus(query)}"
        try:
            response = requests.get(search_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            continue
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            url = normalize_news_url(str(link["href"]))
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= limit:
                break
    return urls


def fetch_finance_stream_page(start: int = 0, count: int = 50, keyword: str | None = None) -> list[NewsItem]:
    params = {
        "count": str(count),
        "device": "desktop",
        "documentType": "article,video",
        "id": "search",
        "lang": "zh-Hant-TW",
        "namespace": "news",
        "region": "TW",
        "site": "finance",
        "start": str(start),
        "version": "v1",
        "imageSizes": "498x280,100x100",
    }
    if keyword:
        params["keyword"] = keyword
    response = requests.get(YAHOO_FINANCE_STREAM_API, headers=HEADERS, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    contents = ((data.get("data") or {}).get("stream") or {}).get("contents") or []
    crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    items: list[NewsItem] = []
    for row in contents:
        url_data = row.get("canonicalUrl") or {}
        url = normalize_news_url(str(url_data.get("url") or ""))
        title = clean_text(str(row.get("title") or ""))
        content = clean_news_content(str(row.get("summary") or row.get("description") or ""))
        published_at = parse_any_datetime(str(row.get("pubDate") or ""))
        if not url or not title or not content or not published_at:
            continue
        items.append(
            NewsItem(
                title=title,
                content=content,
                source="Yahoo Finance Archive API",
                published_at=published_at,
                url=url,
                crawled_at=crawled_at,
            )
        )
    return items


def fetch_finance_stream_historical(start_date: date, end_date: date, limit: int) -> list[NewsItem]:
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    start_offset = 0
    page_size = 50
    stale_pages = 0

    while len(items) < limit and stale_pages < 5 and start_offset <= 10000:
        try:
            page = fetch_finance_stream_page(start=start_offset, count=page_size)
        except requests.RequestException:
            break
        if not page:
            break

        page_dates = [parse_datetime_date(item.published_at) for item in page]
        page_has_target_range = False
        for item, published_date in zip(page, page_dates):
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            if not published_date:
                continue
            if start_date <= published_date <= end_date:
                page_has_target_range = True
                items.append(item)
                if len(items) >= limit:
                    break

        oldest = min((d for d in page_dates if d), default=None)
        newest = max((d for d in page_dates if d), default=None)
        if oldest and oldest < start_date and newest and newest < start_date:
            stale_pages += 1
        else:
            stale_pages = 0
        start_offset += page_size
    return items


def fetch_finance_keyword_historical(
    start_date: date,
    end_date: date,
    limit: int,
    keywords: list[str] | None = None,
) -> list[NewsItem]:
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    page_size = 50
    terms = keywords or DEFAULT_FINANCE_API_KEYWORDS

    for keyword in terms:
        stale_pages = 0
        for start_offset in range(0, 2050, page_size):
            if len(items) >= limit:
                return items
            try:
                page = fetch_finance_stream_page(start=start_offset, count=page_size, keyword=keyword)
            except requests.RequestException:
                break
            if not page:
                break

            page_dates = [parse_datetime_date(item.published_at) for item in page]
            page_has_target_range = False
            for item, published_date in zip(page, page_dates):
                if item.url in seen_urls:
                    continue
                seen_urls.add(item.url)
                if not published_date:
                    continue
                if start_date <= published_date <= end_date:
                    page_has_target_range = True
                    item.source = f"Yahoo Finance Search API:{keyword}"
                    items.append(item)
                    if len(items) >= limit:
                        return items

            newest = max((d for d in page_dates if d), default=None)
            if newest and newest < start_date:
                stale_pages += 1
                if stale_pages >= 3:
                    break
            elif page_has_target_range:
                stale_pages = 0
    return items


def fetch_rss_news(limit: int = 100) -> list[NewsItem]:
    response = requests.get(YAHOO_RSS_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "xml")
    crawled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    items: list[NewsItem] = []

    for node in soup.find_all("item")[:limit]:
        title = clean_text(node.title.get_text()) if node.title else ""
        url = clean_text(node.link.get_text()) if node.link else ""
        description = clean_text(node.description.get_text()) if node.description else ""
        published_at = parse_rss_datetime(node.pubDate.get_text() if node.pubDate else None)
        content = description
        if url:
            try:
                article_content = fetch_article_content(url)
                if len(article_content) > len(content):
                    content = article_content
            except requests.RequestException:
                pass
        if title and url:
            items.append(
                NewsItem(
                    title=title,
                    content=content,
                    source="Yahoo Stock RSS",
                    published_at=published_at,
                    url=url,
                    crawled_at=crawled_at,
                )
            )
    return items


def fetch_yahoo_news(limit: int = 100) -> list[NewsItem]:
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    def add(item: NewsItem | None) -> None:
        if not item:
            return
        if not item.title or not item.content or not item.published_at:
            return
        title_key = item.title.casefold()
        if item.url in seen_urls or title_key in seen_titles:
            return
        seen_urls.add(item.url)
        seen_titles.add(title_key)
        items.append(item)

    for item in fetch_rss_news(limit=max(limit, 50)):
        add(item)
        if len(items) >= limit:
            return items

    for url in discover_page_urls(limit=limit * 2):
        if len(items) >= limit:
            break
        if url in seen_urls:
            continue
        try:
            add(fetch_article(url))
        except requests.RequestException:
            continue
    return items


def fetch_yahoo_historical_news(
    start_date: str,
    end_date: str,
    limit: int = 300,
    search_terms: list[str] | None = None,
) -> list[NewsItem]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    terms = search_terms or DEFAULT_HISTORICAL_SEARCH_TERMS
    items: list[NewsItem] = []
    seen_urls: set[str] = set()

    for item in fetch_finance_keyword_historical(start, end, limit=limit):
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        items.append(item)
        if len(items) >= limit:
            return items

    for item in fetch_finance_stream_historical(start, end, limit=limit - len(items)):
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        items.append(item)
        if len(items) >= limit:
            return items

    candidate_urls = discover_search_urls(terms, start, end, limit=max((limit - len(items)) * 8, 500))
    candidate_urls.extend(discover_page_urls(limit=limit * 2))

    for url in candidate_urls:
        if len(items) >= limit:
            break
        if url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            item = fetch_article(url)
        except requests.RequestException:
            continue
        if not item:
            continue
        published_date = parse_datetime_date(item.published_at)
        if not published_date or published_date < start or published_date > end:
            continue
        items.append(item)
    return items
