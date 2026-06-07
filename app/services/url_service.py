import time
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.metrics import app_metrics
from app.models.click_event import ClickEvent
from app.models.url import Url
from app.schemas.url import (
    AnalyticsResponse,
    ClickEventResponse,
    DeleteResponse,
    ShortenRequest,
    ShortenResponse,
    UrlMetadataResponse,
)
from app.services.cache import UrlCache
from app.services.click_queue import ClickQueue
from app.services.short_code import (
    generate_unique_code,
    hash_ip,
    validate_custom_alias,
    validate_long_url,
)


class UrlService:
    def __init__(
        self,
        session: Session,
        cache: UrlCache,
        click_queue: ClickQueue,
    ) -> None:
        self.session = session
        self.cache = cache
        self.click_queue = click_queue

    def create_short_url(self, request: ShortenRequest) -> ShortenResponse:
        try:
            long_url = validate_long_url(str(request.long_url))
            if request.custom_alias:
                validate_custom_alias(request.custom_alias)
                short_code = request.custom_alias
                custom_alias = True
            else:
                existing = set(self.session.exec(select(Url.short_code)).all())
                short_code = generate_unique_code(existing)
                custom_alias = False
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        existing_url = self.session.exec(select(Url).where(Url.short_code == short_code)).first()
        if existing_url and existing_url.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Short code already exists",
            )

        url = Url(
            short_code=short_code,
            long_url=long_url,
            custom_alias=custom_alias,
            expires_at=request.expires_at,
        )
        self.session.add(url)
        self.session.commit()
        self.session.refresh(url)

        app_metrics.record_url_created()

        return ShortenResponse(
            short_code=url.short_code,
            short_url=f"{settings.base_url.rstrip('/')}/{url.short_code}",
            long_url=url.long_url,
            custom_alias=url.custom_alias,
            expires_at=url.expires_at,
        )

    def get_metadata(self, short_code: str) -> UrlMetadataResponse:
        url = self._get_active_url(short_code)
        return UrlMetadataResponse(
            short_code=url.short_code,
            long_url=url.long_url,
            created_at=url.created_at,
            expires_at=url.expires_at,
            total_clicks=url.total_clicks,
            cached=self.cache.is_cached(short_code),
            active=True,
        )

    def delete_url(self, short_code: str) -> DeleteResponse:
        url = self.session.exec(select(Url).where(Url.short_code == short_code)).first()
        if not url or url.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

        url.deleted_at = datetime.utcnow()
        self.session.add(url)
        self.session.commit()
        self.cache.delete(short_code)

        return DeleteResponse(short_code=short_code, deleted=True)

    def resolve_redirect(
        self,
        short_code: str,
        client_ip: str,
        user_agent: Optional[str],
        referrer: Optional[str],
    ) -> tuple[str, bool, float]:
        start = time.perf_counter()
        cached = self.cache.get(short_code)
        cache_hit = cached is not None

        if cache_hit:
            if cached.get("deleted"):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
            expires_at = cached.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) <= datetime.utcnow():
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL has expired")
            long_url = cached["long_url"]
        else:
            url = self._get_active_url(short_code, allow_expired_check=True)
            long_url = url.long_url
            self._write_cache(url)

        latency_ms = (time.perf_counter() - start) * 1000
        app_metrics.record_redirect(cache_hit=cache_hit, latency_ms=latency_ms)

        self.click_queue.enqueue(
            {
                "short_code": short_code,
                "ip_hash": hash_ip(client_ip),
                "user_agent": user_agent,
                "referrer": referrer,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        return long_url, cache_hit, latency_ms

    def get_analytics(self, short_code: str) -> AnalyticsResponse:
        url = self._get_active_url(short_code)
        all_events = self.session.exec(
            select(ClickEvent).where(ClickEvent.short_code == short_code)
        ).all()
        recent = sorted(all_events, key=lambda e: e.created_at, reverse=True)[:50]

        clicks_by_day: dict[str, int] = {}
        clicks_by_hour: dict[str, int] = {}
        for event in all_events:
            day_key = event.created_at.strftime("%Y-%m-%d")
            hour_key = event.created_at.strftime("%Y-%m-%d %H:00")
            clicks_by_day[day_key] = clicks_by_day.get(day_key, 0) + 1
            clicks_by_hour[hour_key] = clicks_by_hour.get(hour_key, 0) + 1

        return AnalyticsResponse(
            short_code=short_code,
            total_clicks=url.total_clicks,
            clicks_by_day=clicks_by_day,
            clicks_by_hour=clicks_by_hour,
            recent_events=[
                ClickEventResponse(
                    ip_hash=e.ip_hash,
                    user_agent=e.user_agent,
                    referrer=e.referrer,
                    created_at=e.created_at,
                )
                for e in recent
            ],
        )

    def _get_active_url(self, short_code: str, allow_expired_check: bool = False) -> Url:
        url = self.session.exec(select(Url).where(Url.short_code == short_code)).first()
        if not url or url.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
        if allow_expired_check and url.expires_at and url.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL has expired")
        return url

    def _write_cache(self, url: Url) -> None:
        payload = {
            "long_url": url.long_url,
            "expires_at": url.expires_at.isoformat() if url.expires_at else None,
            "deleted": False,
        }
        self.cache.set(url.short_code, payload)

    @staticmethod
    def increment_click_count(session: Session, short_code: str) -> None:
        url = session.exec(select(Url).where(Url.short_code == short_code)).first()
        if not url:
            return
        url.total_clicks += 1
        session.add(url)
        session.commit()

    @staticmethod
    def persist_click_event(session: Session, event: dict) -> None:
        click = ClickEvent(
            short_code=event["short_code"],
            ip_hash=event["ip_hash"],
            user_agent=event.get("user_agent"),
            referrer=event.get("referrer"),
            created_at=datetime.fromisoformat(event["created_at"])
            if event.get("created_at")
            else datetime.utcnow(),
        )
        session.add(click)
        session.commit()
