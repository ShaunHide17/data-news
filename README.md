# data-news

Automated digest of releases and updates from data platforms and open source tooling. Scrapers collect blog posts into a local DuckDB database; an MCP server exposes the data to Claude.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

Clone the repo and install dependencies:

```bash
git clone <repo-url>
cd data-news
uv sync
```

Initialise the DuckDB database and seed the source registry:

```bash
uv run python db.py
```

This creates `data_news.duckdb` in the project root and populates the `source` table with the default platforms (Databricks, Snowflake, Google BigQuery, Palantir, Open Source). Running it again is safe — existing rows are not duplicated.

## Scraping

Run a scraper to populate the database. Summaries require an Anthropic API key.

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run python scrape_databricks.py
```

Re-running is safe — existing records are updated (backfilling any `NULL` author, content, or summary fields) rather than duplicated.

See [docs/scrapers.md](docs/scrapers.md) for details on how each scraper works and how to add a new one.

## MCP server

`mcp_server.py` exposes the database to Claude via the [Model Context Protocol](https://modelcontextprotocol.io). Three tools are available:

| Tool | Description |
|---|---|
| `list_posts` | Sortable, searchable table of posts (newest first). Args: `limit` (default 10), `since` (YYYY-MM-DD). |
| `get_post` | Full scraped text of a post for reading and Q&A. Arg: `url`. |
| `get_post_summary` | AI-generated 2–3 sentence summary. Arg: `url`. |

`list_posts` renders as an interactive [Prefab](https://prefab.prefect.io) table in Claude Desktop — click any row to open the article.

### Register in Claude Desktop

Add the following to `~/Library/Application Support/Claude/claude_desktop_config.json` (create the file if it does not exist):

```json
{
  "mcpServers": {
    "data-news": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/absolute/path/to/data-news"
    }
  }
}
```

Replace `/absolute/path/to/data-news` with the actual path on your machine. Restart Claude Desktop after saving.

### Register in Claude Code

Run inside the project directory:

```bash
claude mcp add data-news -- uv run python mcp_server.py
```

## Project structure

```
data-news/
├── docs/
│   └── scrapers.md        # Scraper architecture and field reference
├── scrapers/
│   ├── base.py            # BaseScraper ABC
│   └── databricks.py      # Databricks blog scraper
├── models.py              # Pydantic models: Source, BlogPost, Category
├── db.py                  # DuckDB schema, init, and query helpers
├── mcp_server.py          # FastMCP server (list_posts, get_post, get_post_summary)
├── scrape_databricks.py   # CLI entry point for the Databricks scraper
├── data_news.duckdb       # Database (created locally, not committed)
└── pyproject.toml
```
