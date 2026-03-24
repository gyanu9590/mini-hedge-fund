"""
src/data/news_fetcher.py

Fetches stock news headlines.

Sources (in priority order)
---------------------------
1. NewsAPI   — requires NEWSAPI_KEY in .env
2. yfinance  — free, no key needed (limited headlines)
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def fetch_stock_news(symbol: str, max_articles: int = 10) -> list[str]:
    """
    Returns a list of headline strings for the given symbol.
    Falls back gracefully if an API key is missing.
    """
    headlines = _from_newsapi(symbol, max_articles)
    if not headlines:
        headlines = _from_yfinance(symbol, max_articles)
    return headlines


# ── NewsAPI ───────────────────────────────────────────────────────────────────
def _from_newsapi(symbol: str, n: int) -> list[str]:
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        return []
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": symbol, "pageSize": n, "language": "en", "sortBy": "publishedAt"},
            headers={"X-Api-Key": key},
            timeout=10,
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [a["title"] for a in articles if a.get("title")]
    except Exception as e:
        logger.warning("NewsAPI fetch failed for %s: %s", symbol, e)
        return []


# ── yfinance fallback ─────────────────────────────────────────────────────────
def _from_yfinance(symbol: str, n: int) -> list[str]:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol + ".NS")
        news   = ticker.news or []
        return [item.get("title", "") for item in news[:n] if item.get("title")]
    except Exception as e:
        logger.warning("yfinance news fetch failed for %s: %s", symbol, e)
        return []