from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.url import (
    AnalyticsResponse,
    DeleteResponse,
    ShortenRequest,
    ShortenResponse,
    UrlMetadataResponse,
)
from app.services.cache import UrlCache
from app.services.click_queue import ClickQueue
from app.services.url_service import UrlService

router = APIRouter(tags=["urls"])


def get_cache() -> UrlCache:
    return UrlCache()


def get_click_queue() -> ClickQueue:
    return ClickQueue()


def get_url_service(
    session: Session = Depends(get_session),
    cache: UrlCache = Depends(get_cache),
    click_queue: ClickQueue = Depends(get_click_queue),
) -> UrlService:
    return UrlService(session, cache, click_queue)


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten_url(
    request: ShortenRequest,
    service: UrlService = Depends(get_url_service),
) -> ShortenResponse:
    return service.create_short_url(request)


@router.get("/urls/{short_code}", response_model=UrlMetadataResponse)
def get_url_metadata(
    short_code: str,
    service: UrlService = Depends(get_url_service),
) -> UrlMetadataResponse:
    return service.get_metadata(short_code)


@router.get("/urls/{short_code}/analytics", response_model=AnalyticsResponse)
def get_url_analytics(
    short_code: str,
    service: UrlService = Depends(get_url_service),
) -> AnalyticsResponse:
    return service.get_analytics(short_code)


@router.delete("/urls/{short_code}", response_model=DeleteResponse)
def delete_url(
    short_code: str,
    service: UrlService = Depends(get_url_service),
) -> DeleteResponse:
    return service.delete_url(short_code)
