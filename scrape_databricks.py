from db import init_db, insert_post
from scrapers import DatabricksScraper

init_db()

with DatabricksScraper() as scraper:
    posts = scraper.get_posts(limit=100)

print(f"Scraped {len(posts)} posts\n")

inserted = 0
for post in posts:
    post_id = insert_post(post)
    status = f"inserted (id={post_id})" if post_id else "skipped (duplicate)"
    date = post.published_at.date() if post.published_at else "unknown date"
    print(f"  [{status:<22}] {date} | {post.title[:60]}")
    if post_id:
        inserted += 1

print(f"\n{inserted} new, {len(posts) - inserted} already in db")
