from fastapi import APIRouter

from app.schemas.url import MetricsResponse
from app.services.metrics_service import get_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    return get_metrics()
