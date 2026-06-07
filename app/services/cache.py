import json
from typing import Any, Optional

import redis

from app.core.config import settings


class UrlCache:
    """Redis cache-aside store for short code -> URL metadata."""

    def __init__(self, client: Optional[redis.Redis] = None) -> None:
        self._client = client or redis.from_url(settings.redis_url, decode_responses=True)
        self.ttl_seconds = settings.cache_ttl_seconds
        self.key_prefix = settings.cache_key_prefix

    @property
    def client(self) -> redis.Redis:
        return self._client

    def ping(self) -> bool:
        return bool(self._client.ping())

    def _key(self, short_code: str) -> str:
        return f"{self.key_prefix}{short_code}"

    def get(self, short_code: str) -> Optional[dict[str, Any]]:
        raw = self._client.get(self._key(short_code))
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, short_code: str, payload: dict[str, Any]) -> None:
        self._client.setex(self._key(short_code), self.ttl_seconds, json.dumps(payload))

    def delete(self, short_code: str) -> None:
        self._client.delete(self._key(short_code))

    def is_cached(self, short_code: str) -> bool:
        return bool(self._client.exists(self._key(short_code)))

    def clear(self) -> None:
        for key in self._client.scan_iter(match=f"{self.key_prefix}*"):
            self._client.delete(key)
