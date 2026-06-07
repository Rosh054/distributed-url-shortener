import logging
import signal
import time
import uuid

import redis

from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import setup_logging
from app.services.click_queue import ClickQueue
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)


class AnalyticsWorker:
    def __init__(self, worker_id: str | None = None) -> None:
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.queue = ClickQueue()
        self.running = True

    def stop(self, *_args) -> None:
        logger.info(
            "Shutdown signal received",
            extra={"event": "shutdown", "worker_id": self.worker_id},
        )
        self.running = False

    def run(self) -> None:
        setup_logging(settings.log_level)
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

        logger.info(
            "Analytics worker started",
            extra={"event": "worker_started", "worker_id": self.worker_id},
        )

        while self.running:
            try:
                event = self.queue.dequeue(timeout=settings.worker_poll_timeout)
            except redis.RedisError:
                logger.warning(
                    "Redis error while dequeuing click event; retrying",
                    extra={"event": "redis_error", "worker_id": self.worker_id},
                )
                time.sleep(1)
                continue

            if event is None:
                continue

            self._process_event(event)

        logger.info(
            "Analytics worker stopped",
            extra={"event": "worker_stopped", "worker_id": self.worker_id},
        )

    def _process_event(self, event: dict) -> None:
        short_code = event.get("short_code", "unknown")
        started = time.perf_counter()

        for attempt in range(1, settings.worker_max_retries + 1):
            try:
                with session_scope() as session:
                    UrlService.persist_click_event(session, event)
                    UrlService.increment_click_count(session, short_code)
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "Click event processed",
                    extra={
                        "event": "click_processed",
                        "worker_id": self.worker_id,
                        "short_code": short_code,
                        "duration_ms": duration_ms,
                    },
                )
                return
            except Exception as exc:
                logger.warning(
                    "Failed to process click event",
                    extra={
                        "event": "click_retry",
                        "worker_id": self.worker_id,
                        "short_code": short_code,
                        "retry_count": attempt,
                        "message": str(exc),
                    },
                )
                if attempt >= settings.worker_max_retries:
                    logger.error(
                        "Click event dropped after max retries",
                        extra={
                            "event": "click_failed",
                            "worker_id": self.worker_id,
                            "short_code": short_code,
                            "retry_count": attempt,
                        },
                    )
                    return
                backoff = settings.worker_base_backoff_seconds * (2 ** (attempt - 1))
                time.sleep(backoff)


def main() -> None:
    AnalyticsWorker().run()


if __name__ == "__main__":
    main()
