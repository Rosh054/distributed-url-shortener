import secrets
import time
from typing import Optional

import redis

from app.core.config import settings
from app.core.metrics import app_metrics

_limiter: Optional["RateLimiter"] = None


class RateLimiter:
    """Sliding-window rate limiter per client IP using Redis sorted sets."""

    def __init__(self, client: Optional[redis.Redis] = None) -> None:
        self._client = client or redis.from_url(settings.redis_url, decode_responses=True)
        self.limit = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds

    @property
    def client(self) -> redis.Redis:
        return self._client

    def _key(self, client_ip: str) -> str:
        return f"ratelimit:{client_ip}"

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        key = self._key(client_ip)

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        member = f"{now}:{secrets.token_hex(4)}"
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds + 1)
        _, _, count, _ = pipe.execute()

        if count > self.limit:
            app_metrics.record_rate_limited()
            return False
        return True

    def reset(self, client_ip: str) -> None:
        self._client.delete(self._key(client_ip))

    def clear_all(self) -> None:
        for key in self._client.scan_iter(match="ratelimit:*"):
            self._client.delete(key)


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_rate_limiter(client: Optional[redis.Redis] = None) -> None:
    global _limiter
    _limiter = RateLimiter(client=client) if client else None
