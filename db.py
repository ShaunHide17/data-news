import duckdb
from datetime import datetime
from pathlib import Path

from models import SOURCES, BlogPost, Source, SourceType

DB_PATH = Path(__file__).parent / "data_news.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS source (
                slug     VARCHAR PRIMARY KEY,
                name     VARCHAR NOT NULL,
                type     VARCHAR NOT NULL,
                blog_url VARCHAR
            )
        """)
        conn.execute("CREATE SEQUENCE IF NOT EXISTS blog_post_id_seq")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blog_post (
                id           INTEGER DEFAULT nextval('blog_post_id_seq') PRIMARY KEY,
                title        VARCHAR NOT NULL,
                url          VARCHAR NOT NULL UNIQUE,
                source_slug  VARCHAR NOT NULL REFERENCES source(slug),
                category     VARCHAR NOT NULL,
                author       VARCHAR,
                published_at TIMESTAMP,
                retrieved_at TIMESTAMP NOT NULL,
                summary      VARCHAR,
                content      VARCHAR
            )
        """)
        conn.executemany(
            "INSERT INTO source VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [
                (s.slug, s.name, s.type.value, str(s.blog_url) if s.blog_url else None)
                for s in SOURCES.values()
            ],
        )


def insert_post(post: BlogPost) -> int | None:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM blog_post WHERE url = ?", [str(post.url)]
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE blog_post SET
                    author  = COALESCE(author, ?),
                    content = COALESCE(content, ?),
                    summary = COALESCE(summary, ?)
                WHERE url = ?
                """,
                [post.author, post.content, post.summary, str(post.url)],
            )
            return None

        result = conn.execute(
            """
            INSERT INTO blog_post
                (title, url, source_slug, category, author, published_at, retrieved_at, summary, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                post.title,
                str(post.url),
                post.source.slug,
                post.category.value,
                post.author,
                post.published_at,
                post.retrieved_at,
                post.summary,
                post.content,
            ],
        )
        return result.fetchone()[0]


def get_posts(source_slug: str | None = None) -> list[BlogPost]:
    query = """
        SELECT bp.title, bp.url, bp.category, bp.author, bp.published_at, bp.retrieved_at,
               bp.summary, bp.content, s.slug, s.name, s.type, s.blog_url
        FROM blog_post bp
        JOIN source s ON bp.source_slug = s.slug
        {where}
    """
    with get_connection() as conn:
        if source_slug:
            rows = conn.execute(
                query.format(where="WHERE bp.source_slug = ?"), [source_slug]
            ).fetchall()
        else:
            rows = conn.execute(query.format(where="")).fetchall()
        return [_row_to_post(row) for row in rows]


def _row_to_post(row: tuple) -> BlogPost:
    title, url, category, author, published_at, retrieved_at, summary, content, slug, name, stype, blog_url = row
    return BlogPost(
        title=title,
        url=url,
        source=Source(slug=slug, name=name, type=SourceType(stype), blog_url=blog_url),
        category=category,
        author=author,
        published_at=published_at,
        retrieved_at=retrieved_at,
        summary=summary,
        content=content,
    )


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
    with get_connection() as conn:
        sources = conn.execute("SELECT slug, name, type FROM source").fetchall()
        print(f"Seeded {len(sources)} sources:")
        for slug, name, stype in sources:
            print(f"  {slug:<20} {stype:<25} {name}")
