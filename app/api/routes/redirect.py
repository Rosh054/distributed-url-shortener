from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.database import get_session
from app.services.cache import UrlCache
from app.services.click_queue import ClickQueue
from app.services.url_service import UrlService

router = APIRouter(tags=["redirect"])


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


@router.get("/{short_code}")
def redirect_to_long_url(
    short_code: str,
    request: Request,
    response: Response,
    service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    long_url, cache_hit, latency_ms = service.resolve_redirect(
        short_code=short_code,
        client_ip=client_ip,
        user_agent=user_agent,
        referrer=referrer,
    )

    redirect = RedirectResponse(url=long_url, status_code=302)
    redirect.headers["X-Cache-Hit"] = "true" if cache_hit else "false"
    redirect.headers["X-Redirect-Latency-Ms"] = str(round(latency_ms, 3))
    return redirect
