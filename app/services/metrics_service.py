from app.core.metrics import app_metrics
from app.schemas.url import MetricsResponse


def get_metrics() -> MetricsResponse:
    snapshot = app_metrics.snapshot()
    return MetricsResponse(
        redirect_count=snapshot["redirect_count"],
        cache_hit_count=snapshot["cache_hit_count"],
        cache_miss_count=snapshot["cache_miss_count"],
        cache_hit_rate=round(snapshot["cache_hit_rate"], 4),
        average_redirect_latency_ms=round(snapshot["average_redirect_latency_ms"], 3),
        urls_created_count=snapshot["urls_created_count"],
        rate_limited_count=snapshot["rate_limited_count"],
    )
