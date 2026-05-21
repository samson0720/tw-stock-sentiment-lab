from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


YAHOO_RSS_URL = "https://tw.stock.yahoo.com/rss"
YAHOO_NEWS_URL = "https://tw.stock.yahoo.com/news"
QUOTE_NEWS_URLS = [
    "https://tw.stock.yahoo.com/quote/0050.TW/news",
    "https://tw.stock.yahoo.com/quote/2330.TW/news",
    "https://tw.stock.yahoo.com/quote/2317.TW/news",
    "https://tw.stock.yahoo.com/quote/2454.TW/news",
    "https://tw.stock.yahoo.com/quote/2303.TW/news",
]
HEADERS = {"User-Agent": "Mozilla/5.0 twstock-sentiment-research/0.1"}


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


def parse_rss_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


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
        return parse_rss_datetime(value) or clean_text(value)
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
    return clean_text(max(candidates, key=len, default=""))


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
        source="Yahoo Stock News",
        published_at=published_at,
        url=url,
        crawled_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def normalize_news_url(href: str) -> str | None:
    url = urljoin("https://tw.stock.yahoo.com", href).split("?")[0]
    parsed = urlparse(url)
    if parsed.netloc != "tw.stock.yahoo.com":
        return None
    if not parsed.path.startswith("/news/") or parsed.path == "/news/":
        return None
    if not parsed.path.endswith(".html"):
        return None
    return url


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
