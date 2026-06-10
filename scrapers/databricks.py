import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import anthropic

from models import BlogPost, Category, SOURCES

from .base import BaseScraper

BASE_URL = "https://www.databricks.com"
BLOG_PATH = "/blog"
SITEMAP_URL = f"{BASE_URL}/en-blog-assets/sitemap/sitemap-index.xml"

_CATEGORY_MAP: dict[str, Category] = {
    "engineering": Category.ENGINEERING,
    "product": Category.PRODUCT_UPDATE,
    "platform": Category.PRODUCT_UPDATE,
    "announcements": Category.PRODUCT_UPDATE,
    "partners": Category.PARTNERSHIP,
    "company": Category.OTHER,
    "customers": Category.OTHER,
    "ml & ai": Category.FEATURE_RELEASE,
    "machine learning": Category.FEATURE_RELEASE,
    "data engineering": Category.ENGINEERING,
    "data science": Category.ENGINEERING,
    "generative ai": Category.FEATURE_RELEASE,
    "open source": Category.FEATURE_RELEASE,
    "financial services": Category.OTHER,
    "telecommunications": Category.OTHER,
    "retail": Category.OTHER,
    "healthcare": Category.OTHER,
    "media": Category.OTHER,
}

# "Wed, 06/10/2026 - 15:52"  or  "06/10/2026"
_META_DATE_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")

_MAX_WORKERS = 10


class DatabricksScraper(BaseScraper):
    source = SOURCES["databricks"]

    def __init__(self, timeout: float = 30.0):
        super().__init__(timeout)
        self._llm = anthropic.Anthropic()

    def get_posts(
        self,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> list[BlogPost]:
        """
        Scrape the Databricks blog.

        limit – collect at most this many posts.
        since – discard posts published before this datetime.
        """
        urls = self._get_post_urls(limit)
        posts = self._fetch_posts_parallel(urls, since=since)
        posts.sort(key=lambda p: p.published_at or datetime.min, reverse=True)
        return posts

    # --- URL discovery ---

    def _get_post_urls(self, limit: int | None) -> list[str]:
        """Return blog post URLs from the sitemap, newest-first, up to limit."""
        idx_resp = self._client.get(SITEMAP_URL)
        idx_resp.raise_for_status()
        child_urls = re.findall(r"<loc>([^<]+)</loc>", idx_resp.text)

        all_urls: list[str] = []
        for child_url in child_urls:
            resp = self._client.get(child_url)
            resp.raise_for_status()
            urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
            for url in urls:
                # Skip author/category/tag index pages
                if re.search(r"/blog/(author|category|tag)/", url):
                    continue
                all_urls.append(url)

        return all_urls[:limit] if limit else all_urls

    # --- Parallel fetching ---

    def _fetch_posts_parallel(
        self,
        urls: list[str],
        since: datetime | None,
    ) -> list[BlogPost]:
        posts: list[BlogPost] = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {executor.submit(self._fetch_post, url): url for url in urls}
            for future in as_completed(futures):
                try:
                    post = future.result()
                except Exception:
                    continue
                if post is None:
                    continue
                if since and post.published_at and post.published_at < since:
                    continue
                posts.append(post)
        return posts

    # --- Single post parser ---

    def _fetch_post(self, url: str) -> BlogPost | None:
        soup = self.fetch(url)

        # Title from og:title (cleaner than h1 which may include site name)
        og_title = soup.find("meta", property="og:title")
        title = og_title["content"].strip() if og_title and og_title.get("content") else None
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else None
        if not title:
            return None

        # Published date from article:published_time meta
        published_at = None
        pub_meta = soup.find("meta", property="article:published_time")
        if pub_meta and pub_meta.get("content"):
            m = _META_DATE_RE.search(pub_meta["content"])
            if m:
                published_at = self._parse_date(m.group(1))

        # Category and author: the post <header> contains
        # "{category} | {date} | {title} | {desc} | by | {author}"
        category = Category.OTHER
        author = None
        header = soup.find("header")
        if header:
            parts = [p.strip() for p in header.get_text(separator="|", strip=True).split("|")]
            for part in parts:
                lower = part.lower()
                if lower in _CATEGORY_MAP:
                    category = _CATEGORY_MAP[lower]
                    break
            # Author follows "by"
            for i, part in enumerate(parts):
                if part.lower() == "by" and i + 1 < len(parts):
                    candidate = parts[i + 1].strip()
                    # Sanity: author names are short and don't contain dates
                    if candidate and len(candidate) < 80 and not _META_DATE_RE.search(candidate):
                        author = candidate
                    break

        content = None
        body = soup.select_one(".article--content.rich-text-blog")
        if body:
            content = body.get_text(separator="\n", strip=True)

        summary = self._summarize(content) if content else None

        return BlogPost(
            title=title,
            url=url,  # type: ignore[arg-type]
            source=self.source,
            category=category,
            author=author,
            published_at=published_at,
            content=content,
            summary=summary,
        )

    def _summarize(self, content: str) -> str | None:
        try:
            response = self._llm.messages.create(
                model="claude-opus-4-8",
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": (
                        "Summarise the following blog post in 2-3 sentences for a technical audience.\n\n"
                        + content[:10_000]
                    ),
                }],
            )
            return next((b.text for b in response.content if b.type == "text"), None)
        except Exception:
            return None
