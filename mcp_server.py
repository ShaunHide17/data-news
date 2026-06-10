"""MCP server exposing the Databricks blog database."""

from __future__ import annotations

from datetime import datetime

from fastmcp import FastMCP
from prefab_ui.actions import OpenLink
from prefab_ui.app import PrefabApp
from prefab_ui.components import DataTable, DataTableColumn
from prefab_ui.rx import EVENT

from db import get_posts as db_get_posts, init_db

mcp = FastMCP(
    "data-news",
    instructions=(
        "Provides read access to the Databricks engineering blog database. "
        "Use list_posts to browse recent articles, get_post to read one in full "
        "for Q&A, and get_post_summary for a quick AI-generated overview."
    ),
)


@mcp.tool(app=True)
def list_posts(limit: int = 10, since: str | None = None) -> PrefabApp:
    """List Databricks blog posts sorted by date, newest first.

    Args:
        limit: Maximum number of posts to return (default 10, max 100).
        since: Only include posts published on or after this date (YYYY-MM-DD).
    """
    init_db()
    posts = db_get_posts(source_slug="databricks")
    posts.sort(key=lambda p: p.published_at or datetime.min, reverse=True)

    if since:
        cutoff = datetime.fromisoformat(since)
        posts = [p for p in posts if p.published_at and p.published_at >= cutoff]

    posts = posts[: min(limit, 100)]

    rows = [
        {
            "title": post.title,
            "author": post.author or "—",
            "date": post.published_at.strftime("%Y-%m-%d") if post.published_at else "—",
            "category": post.category.replace("_", " ").title(),
            "url": str(post.url),
        }
        for post in posts
    ]

    table = DataTable(
        columns=[
            DataTableColumn(key="title", header="Title", sortable=True),
            DataTableColumn(key="author", header="Author", sortable=True),
            DataTableColumn(key="date", header="Date", sortable=True, width="110px"),
            DataTableColumn(key="category", header="Category", sortable=True, width="150px"),
        ],
        rows=rows,
        search=True,
        paginated=True,
        pageSize=min(limit, 25),
        onRowClick=OpenLink(url=EVENT.url),
    )

    return PrefabApp(title="Databricks Blog", view=table)


@mcp.tool()
def get_post(url: str) -> str:
    """Return the full scraped text of a blog post for reading and Q&A.

    Args:
        url: The exact URL of the post (copy from list_posts output).
    """
    init_db()
    posts = db_get_posts(source_slug="databricks")
    post = next(
        (p for p in posts if str(p.url).rstrip("/") == url.rstrip("/")), None
    )

    if not post:
        return f"Post not found in database: {url}"
    if not post.content:
        return f'No content stored for "{post.title}". Re-run the scraper to populate it.'

    parts = [f"# {post.title}"]
    if post.author:
        parts.append(f"**Author:** {post.author}")
    if post.published_at:
        parts.append(f"**Published:** {post.published_at.strftime('%Y-%m-%d')}")
    parts.append(f"**URL:** {post.url}\n")
    parts.append(post.content)
    return "\n".join(parts)


@mcp.tool()
def get_post_summary(url: str) -> str:
    """Return the AI-generated 2-3 sentence summary of a blog post.

    Args:
        url: The exact URL of the post (copy from list_posts output).
    """
    init_db()
    posts = db_get_posts(source_slug="databricks")
    post = next(
        (p for p in posts if str(p.url).rstrip("/") == url.rstrip("/")), None
    )

    if not post:
        return f"Post not found in database: {url}"
    if not post.summary:
        return f'No summary stored for "{post.title}". Re-run the scraper to generate one.'

    return f"**{post.title}**\n\n{post.summary}"


if __name__ == "__main__":
    mcp.run()
