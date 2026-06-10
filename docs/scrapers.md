# Scrapers

Scrapers live in `scrapers/` and all extend `BaseScraper`. Each scraper is responsible for one source: discovering post URLs, fetching article pages, and returning a list of `BlogPost` objects ready to be inserted into DuckDB.

## Architecture

```
scrapers/
├── base.py          # BaseScraper ABC
└── databricks.py    # DatabricksScraper
```

### BaseScraper (`scrapers/base.py`)

Abstract base class that all scrapers must extend.

**Provides:**
- `self._client` — a shared `httpx.Client` configured with a 30 s timeout, redirect following, and a `User-Agent` header
- `fetch(url) -> BeautifulSoup` — GET a URL and parse the response with `lxml`
- `_parse_date(raw) -> datetime | None` — parse common date string formats (`%B %d, %Y`, `%Y-%m-%d`, `%m/%d/%Y`, etc.)
- Context manager support (`with DatabricksScraper() as s:`) that closes the HTTP client on exit

**Requires subclasses to implement:**
- `source: Source` — class-level attribute identifying the data source
- `get_posts(limit, since) -> list[BlogPost]` — entry point called by scrape scripts

---

## Databricks (`scrapers/databricks.py`)

Scrapes the [Databricks engineering blog](https://www.databricks.com/blog).

### Discovery

URLs are pulled from the XML sitemap index at:

```
https://www.databricks.com/en-blog-assets/sitemap/sitemap-index.xml
```

The index lists child sitemaps; each child is fetched in turn and `<loc>` entries are extracted. Index pages (`/blog/author/`, `/blog/category/`, `/blog/tag/`) are filtered out, leaving individual article URLs.

### Per-article parsing

Each article page is fetched and parsed for:

| Field | Source |
|---|---|
| `title` | `og:title` meta tag, falling back to `<h1>` |
| `published_at` | `article:published_time` meta tag (format: `Wed, 06/10/2026 - 15:52`) |
| `category` | First token in the `<header>` element matched against a category map |
| `author` | Token immediately following `"by"` in the `<header>` element |
| `content` | `.article--content.rich-text-blog` div, extracted as plain text |
| `summary` | LLM-generated via `claude-opus-4-8` (first 10 000 chars of content) |

### Parallelism

Articles are fetched with a `ThreadPoolExecutor` (10 workers). Summarisation calls the Anthropic API synchronously inside each worker thread.

### Configuration

| Parameter | Default | Description |
|---|---|---|
| `limit` | `None` | Cap the number of posts returned |
| `since` | `None` | Discard posts published before this `datetime` |
| `timeout` | `30.0 s` | Per-request HTTP timeout |

### Environment

`ANTHROPIC_API_KEY` must be set for summary generation. Without it the `_summarize` call fails silently and `summary` is stored as `None`.

### Usage

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run python scrape_databricks.py
```

Or import directly:

```python
from scrapers import DatabricksScraper
from db import init_db, insert_post

init_db()
with DatabricksScraper() as scraper:
    for post in scraper.get_posts(limit=20):
        insert_post(post)
```

---

## Adding a new scraper

1. Create `scrapers/<source>.py` and subclass `BaseScraper`
2. Set the `source` class attribute to the matching entry from `models.SOURCES`
3. Implement `get_posts(limit, since)` — use `self.fetch(url)` and `self._parse_date(raw)` where possible
4. Export the new class from `scrapers/__init__.py`
5. Add the source slug to `models.SOURCES` if it does not already exist
6. Create a `scrape_<source>.py` script following the same pattern as `scrape_databricks.py`
