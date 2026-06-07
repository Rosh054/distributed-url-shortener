from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_alias: Optional[str] = Field(default=None, max_length=64)
    expires_at: Optional[datetime] = None


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    custom_alias: bool
    expires_at: Optional[datetime] = None


class UrlMetadataResponse(BaseModel):
    short_code: str
    long_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    total_clicks: int
    cached: bool
    active: bool


class ClickEventResponse(BaseModel):
    ip_hash: str
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    created_at: datetime


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    clicks_by_day: dict[str, int]
    clicks_by_hour: dict[str, int]
    recent_events: list[ClickEventResponse]


class HealthResponse(BaseModel):
    status: str
    api: str
    redis: str
    postgres: str


class MetricsResponse(BaseModel):
    redirect_count: int
    cache_hit_count: int
    cache_miss_count: int
    cache_hit_rate: float
    average_redirect_latency_ms: float
    urls_created_count: int
    rate_limited_count: int


class DeleteResponse(BaseModel):
    short_code: str
    deleted: bool
