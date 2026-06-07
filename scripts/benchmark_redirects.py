#!/usr/bin/env python3
"""Benchmark cached vs uncached redirect latency."""

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import redis


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    index = int(round((pct / 100.0) * (len(sorted_vals) - 1)))
    return round(sorted_vals[index], 3)


def clear_rate_limits(redis_client: redis.Redis) -> None:
    """Clear sliding-window counters so benchmarks measure cache latency, not rate limits."""
    for key in redis_client.scan_iter(match="ratelimit:*"):
        redis_client.delete(key)


def measure_redirect(
    client: httpx.Client,
    code: str,
    redis_client: redis.Redis | None = None,
) -> float:
    if redis_client is not None:
        clear_rate_limits(redis_client)
    start = time.perf_counter()
    response = client.get(f"/{code}", follow_redirects=False)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if response.status_code == 429:
        raise RuntimeError(
            "Rate limit hit during benchmark. Ensure Redis is reachable at "
            f"{os.getenv('REDIS_URL', 'redis://localhost:6379/0')} so the script "
            "can clear rate-limit keys, or raise RATE_LIMIT_REQUESTS in docker-compose."
        )
    if response.status_code not in (301, 302):
        response.raise_for_status()
    return elapsed_ms


def measure_redirects(
    client: httpx.Client,
    code: str,
    samples: int,
    redis_client: redis.Redis | None = None,
) -> list[float]:
    return [measure_redirect(client, code, redis_client) for _ in range(samples)]


def sustained_throughput(
    client: httpx.Client,
    code: str,
    duration_seconds: float,
    redis_client: redis.Redis | None = None,
) -> float:
    end = time.time() + duration_seconds
    count = 0
    while time.time() < end:
        if redis_client is not None:
            clear_rate_limits(redis_client)
        response = client.get(f"/{code}", follow_redirects=False)
        if response.status_code == 302:
            count += 1
    return round(count / duration_seconds, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark redirect latency")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    parser.add_argument("--cache-prefix", default=os.getenv("CACHE_KEY_PREFIX", "url:cache:"))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{timestamp}.json"

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        client.get("/health").raise_for_status()

        create_response = client.post(
            "/shorten",
            json={"long_url": "https://example.com/benchmark-target"},
        )
        create_response.raise_for_status()
        code = create_response.json()["short_code"]
        cache_key = f"{args.cache_prefix}{code}"
        redis_client = redis.from_url(args.redis_url, decode_responses=True)
        clear_rate_limits(redis_client)

        uncached = []
        for _ in range(args.samples):
            redis_client.delete(cache_key)
            uncached.append(measure_redirect(client, code, redis_client))

        measure_redirect(client, code, redis_client)
        cached = measure_redirects(client, code, args.samples, redis_client)
        throughput = sustained_throughput(client, code, args.duration, redis_client)
        metrics = client.get("/metrics").json()

        uncached_p50 = percentile(uncached, 50)
        uncached_p95 = percentile(uncached, 95)
        cached_p50 = percentile(cached, 50)
        cached_p95 = percentile(cached, 95)
        reduction = 0.0
        if uncached_p50 > 0:
            reduction = round(((uncached_p50 - cached_p50) / uncached_p50) * 100, 2)

        result = {
            "timestamp": timestamp,
            "base_url": args.base_url,
            "short_code": code,
            "samples_per_phase": args.samples,
            "uncached_redirect_latency_ms": {
                "p50": uncached_p50,
                "p95": uncached_p95,
                "mean": round(statistics.mean(uncached), 3),
            },
            "cached_redirect_latency_ms": {
                "p50": cached_p50,
                "p95": cached_p95,
                "mean": round(statistics.mean(cached), 3),
            },
            "latency_reduction_percent_p50": reduction,
            "sustained_requests_per_sec": throughput,
            "rate_limit_threshold": int(os.getenv("RATE_LIMIT_REQUESTS", "60")),
            "application_metrics": metrics,
        }

    output_file.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"\nSaved benchmark results to {output_file}")


if __name__ == "__main__":
    main()
