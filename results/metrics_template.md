# URL Shortener Metrics

Benchmark source: `results/benchmark_20260607_012212.json`  
Run date: 2026-06-07  
Environment: local Docker Compose (macOS)

## Local benchmark

- Number of URLs created: 1 (benchmark URL `eUutLNx`; 100 samples per latency phase)
- Cached redirect latency p50: 4.02 ms
- Cached redirect latency p95: 7.73 ms
- Uncached redirect latency p50: 5.05 ms
- Uncached redirect latency p95: 7.40 ms
- Latency reduction from caching: 20.33% (p50)
- Requests/sec sustained: 204.6
- Rate limit threshold: 60 requests/minute/IP
- Error rate: 0% (benchmark run; all 302 redirects succeeded)

### Notes

- Uncached phase clears Redis cache before each sample; cached phase reuses warm cache entries.
- Application cache hit rate after benchmark: 94.1% (`cache_hit_count` / total redirects).
- Benchmark script clears Redis rate-limit keys so measurements reflect cache latency, not throttling.

## AWS benchmark

_Not yet run — fill after ECS deployment._

- ALB URL:
- API task count:
- Sustained redirect requests/sec:
- p95 redirect latency:
- Redis cache hit rate:
