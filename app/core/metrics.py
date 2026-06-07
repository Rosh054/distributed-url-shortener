"""In-memory application metrics for /metrics endpoint."""

import threading
from dataclasses import dataclass, field


@dataclass
class AppMetrics:
    redirect_count: int = 0
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    total_redirect_latency_ms: float = 0.0
    urls_created_count: int = 0
    rate_limited_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_redirect(self, cache_hit: bool, latency_ms: float) -> None:
        with self._lock:
            self.redirect_count += 1
            if cache_hit:
                self.cache_hit_count += 1
            else:
                self.cache_miss_count += 1
            self.total_redirect_latency_ms += latency_ms

    def record_url_created(self) -> None:
        with self._lock:
            self.urls_created_count += 1

    def record_rate_limited(self) -> None:
        with self._lock:
            self.rate_limited_count += 1

    @property
    def cache_hit_rate(self) -> float:
        with self._lock:
            total = self.cache_hit_count + self.cache_miss_count
            if total == 0:
                return 0.0
            return self.cache_hit_count / total

    @property
    def average_redirect_latency_ms(self) -> float:
        with self._lock:
            if self.redirect_count == 0:
                return 0.0
            return self.total_redirect_latency_ms / self.redirect_count

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            redirects = self.redirect_count
            hits = self.cache_hit_count
            misses = self.cache_miss_count
            total_lat = self.total_redirect_latency_ms
            created = self.urls_created_count
            limited = self.rate_limited_count
        lookups = hits + misses
        return {
            "redirect_count": redirects,
            "cache_hit_count": hits,
            "cache_miss_count": misses,
            "cache_hit_rate": (hits / lookups) if lookups else 0.0,
            "average_redirect_latency_ms": (total_lat / redirects) if redirects else 0.0,
            "urls_created_count": created,
            "rate_limited_count": limited,
        }


app_metrics = AppMetrics()
