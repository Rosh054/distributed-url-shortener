from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.core.database import engine
from app.schemas.url import HealthResponse
from app.services.cache import UrlCache
from app.services.click_queue import ClickQueue

router = APIRouter(tags=["health"])


def get_cache() -> UrlCache:
    return UrlCache()


def get_click_queue() -> ClickQueue:
    return ClickQueue()


@router.get("/health", response_model=HealthResponse)
def health(
    cache: UrlCache = Depends(get_cache),
    click_queue: ClickQueue = Depends(get_click_queue),
) -> HealthResponse:
    api_status = "ok"
    redis_status = "down"
    postgres_status = "down"

    try:
        if cache.ping() and click_queue.ping():
            redis_status = "ok"
    except Exception:
        redis_status = "down"

    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
            postgres_status = "ok"
    except Exception:
        postgres_status = "down"

    overall = "ok" if all(s == "ok" for s in (api_status, redis_status, postgres_status)) else "degraded"
    return HealthResponse(
        status=overall,
        api=api_status,
        redis=redis_status,
        postgres=postgres_status,
    )
