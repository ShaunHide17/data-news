from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from models import BlogPost, Source


class BaseScraper(ABC):
    source: Source

    def __init__(self, timeout: float = 30.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "data-news-bot/1.0 (+https://github.com/shaunhide/data-news)"},
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._client.close()

    def close(self):
        self._client.close()

    def fetch(self, url: str) -> BeautifulSoup:
        response = self._client.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    @abstractmethod
    def get_posts(self) -> list[BlogPost]:
        """Scrape the blog index and return a list of BlogPost objects."""
        ...

    def _parse_date(self, raw: str | None) -> datetime | None:
        if not raw:
            return None
        raw = raw.strip()
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y", "%B %Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None
