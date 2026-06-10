# data-news

Automated monthly digest of releases and updates from data platforms and open source tooling.

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

## Create the database

Initialise the DuckDB database and seed the source registry:

```bash
uv run python db.py
```

This creates `data_news.duckdb` in the project root and populates the `source` table with the default platforms (Databricks, Snowflake, Google BigQuery, Palantir, Open Source). Running the command again is safe — existing rows are not duplicated.

## Project structure

```
data-news/
├── models.py          # Pydantic models: Source, BlogPost, Category, SourceType
├── db.py              # DuckDB schema, init, and query helpers
├── data_news.duckdb   # Database (created by db.py, not committed)
└── pyproject.toml
```
