from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class Category(StrEnum):
    FEATURE_RELEASE = "feature_release"
    PRODUCT_UPDATE = "product_update"
    DEPRECATION = "deprecation"
    PARTNERSHIP = "partnership"
    ENGINEERING = "engineering"
    OTHER = "other"


class SourceType(StrEnum):
    CLOUD_DATA_PLATFORM = "cloud_data_platform"
    LAKEHOUSE = "lakehouse"
    AI_DATA_PLATFORM = "ai_data_platform"
    OPEN_SOURCE = "open_source"


class Source(BaseModel):
    slug: str
    name: str
    type: SourceType
    blog_url: Optional[HttpUrl] = None


SOURCES: dict[str, Source] = {
    "databricks": Source(
        slug="databricks",
        name="Databricks",
        type=SourceType.LAKEHOUSE,
        blog_url="https://www.databricks.com/blog",
    ),
    "snowflake": Source(
        slug="snowflake",
        name="Snowflake",
        type=SourceType.CLOUD_DATA_PLATFORM,
        blog_url="https://www.snowflake.com/blog",
    ),
    "bigquery": Source(
        slug="bigquery",
        name="Google BigQuery",
        type=SourceType.CLOUD_DATA_PLATFORM,
        blog_url="https://cloud.google.com/blog/products/data-analytics",
    ),
    "palantir": Source(
        slug="palantir",
        name="Palantir",
        type=SourceType.AI_DATA_PLATFORM,
        blog_url="https://blog.palantir.com",
    ),
    "open_source": Source(
        slug="open_source",
        name="Open Source",
        type=SourceType.OPEN_SOURCE,
    ),
}


class BlogPost(BaseModel):
    title: str
    url: HttpUrl
    source: Source
    category: Category
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = None      # Set on ingest
    summary: Optional[str] = None     # LLM-generated, populated after retrieval
    content: Optional[str] = None     # Raw scraped text

    def model_post_init(self, __context):
        if self.retrieved_at is None:
            self.retrieved_at = datetime.now()
