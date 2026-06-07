import json
from typing import Any, Optional

import redis

from app.core.config import settings


class ClickQueue:
    """Redis list queue for async click analytics."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        queue_key: Optional[str] = None,
        client: Optional[redis.Redis] = None,
    ) -> None:
        self.queue_key = queue_key or settings.redis_click_queue_key
        self._client = client or redis.from_url(redis_url or settings.redis_url, decode_responses=True)

    @property
    def client(self) -> redis.Redis:
        return self._client

    def ping(self) -> bool:
        return bool(self._client.ping())

    def enqueue(self, event: dict[str, Any]) -> None:
        self._client.lpush(self.queue_key, json.dumps(event))

    def dequeue(self, timeout: int = 5) -> Optional[dict[str, Any]]:
        item = self._client.brpop(self.queue_key, timeout=timeout)
        if item is None:
            return None
        _, raw = item
        return json.loads(raw)

    def queue_depth(self) -> int:
        return int(self._client.llen(self.queue_key))

    def clear(self) -> None:
        self._client.delete(self.queue_key)
