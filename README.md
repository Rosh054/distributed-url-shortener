# Distributed URL Shortener

A TinyURL-style distributed URL shortening service built with FastAPI, PostgreSQL, Redis, and Docker. Designed as a resume-grade backend project with cache-aside redirects, async click analytics, per-IP rate limiting, benchmarks, and optional AWS ECS deployment artifacts.

## Architecture

```text
POST /shorten
  |
  v
FastAPI
  |
  v
PostgreSQL stores code -> long URL

GET /{code}
  |
  v
Redis cache lookup
  |
  |-- cache hit -> redirect
  |
  |-- cache miss -> PostgreSQL -> Redis -> redirect

Redirect event -> Redis queue -> analytics worker -> PostgreSQL

Redis also handles rate limiting.
```

```text
                    +------------------+
                    |       ALB        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
       +------v------+               +------v------+
       |  API (ECS)  |               | Worker (ECS)|
       +------+------+               +------+------+
              |                             |
    +---------+---------+                   |
    |                   |                   |
+---v---+         +-----v-----+       +-----v-----+
| Redis |         | PostgreSQL|       | PostgreSQL|
| cache |         |   urls    |       |click_events|
| queue |         +-----------+       +-----------+
| limit |
+-------+
```

## Features

- Base62 short code generation with collision handling and custom aliases
- Cache-aside redirects with configurable TTL and cache hit metrics
- Sliding-window per-IP rate limiting (default 60 req/min)
- Async click analytics via Redis queue and dedicated worker
- Privacy-aware analytics (hashed IPs, no raw IP storage)
- Soft-delete for deactivated URLs with cache invalidation
- `/metrics` endpoint for redirect latency and cache hit rate
- Docker Compose local stack and GitHub Actions CI
- Optional Terraform for AWS (ALB, ECS, RDS, ElastiCache, CloudWatch)

## Tech stack

| Layer | Technologies |
|-------|--------------|
| Language | Python 3.11+ |
| API | FastAPI, Pydantic, Uvicorn |
| Database | PostgreSQL 16, SQLModel |
| Cache / queue | Redis 7 |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| IaC | Terraform (AWS) |
| Testing | pytest, fakeredis, httpx |

## Local setup

```bash
git clone <repo-url>
cd distributed-url-shortener

make setup    # venv + pip install + .env from .env.example
make up       # docker compose up --build -d
make logs     # follow api/worker/postgres/redis logs
```

Verify health:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

## API examples

### Create a short URL

```bash
curl -s -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com/very/long/path"}' | python3 -m json.tool
```

### Custom alias

```bash
curl -s -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com/docs","custom_alias":"my-docs"}'
```

### Redirect (302)

```bash
curl -i http://localhost:8000/my-docs
# X-Cache-Hit: true|false
# X-Redirect-Latency-Ms: ...
```

### URL metadata

```bash
curl -s http://localhost:8000/urls/my-docs | python3 -m json.tool
```

### Analytics

```bash
curl -s http://localhost:8000/urls/my-docs/analytics | python3 -m json.tool
```

### Delete (soft)

```bash
curl -s -X DELETE http://localhost:8000/urls/my-docs
```

### Metrics

```bash
curl -s http://localhost:8000/metrics | python3 -m json.tool
```

## Cache behavior

1. `GET /{code}` checks Redis key `url:cache:{code}`.
2. On **cache miss**, the service loads from PostgreSQL, writes to Redis with TTL (`CACHE_TTL_SECONDS`, default 3600), then redirects.
3. On **cache hit**, redirect skips the database read.
4. `DELETE /urls/{code}` sets `deleted_at` in PostgreSQL and deletes the cache key.
5. Response headers `X-Cache-Hit` and `X-Redirect-Latency-Ms` expose per-request behavior.

## Rate limiting

- Sliding-window limiter in Redis (sorted set per IP).
- Default: **60 requests/minute/IP** on redirect paths (`GET /{code}`).
- Excluded paths: `/health`, `/metrics`, `/shorten`, `/urls/*`, OpenAPI docs.
- Returns **HTTP 429** with `Retry-After` when exceeded.
- Configure via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`.

## Analytics worker

- Redirects enqueue click events to Redis list `clicks:queue`.
- Worker container (`Dockerfile.worker`) consumes events, inserts `click_events` rows, and increments `urls.total_clicks`.
- IP addresses are hashed with `IP_HASH_SALT` before storage.
- Structured JSON logs include `short_code`, `duration_ms`, and retry counts.

## Benchmark instructions

Start the stack, then:

```bash
make generate-urls   # create 100 URLs -> results/generated_urls.json
make benchmark       # cached vs uncached latency -> results/benchmark_*.json
chmod +x scripts/load_test_hey.sh
./scripts/load_test_hey.sh
```

Copy measured values into `results/metrics_template.md`. **Do not invent metrics** — run the scripts locally and fill in real numbers.

## Metrics placeholders

See [`results/metrics_template.md`](results/metrics_template.md) for local and AWS benchmark fields.

## AWS deployment guide

See [`aws/README.md`](aws/README.md) for Terraform apply steps, ECR push commands, and alarm descriptions.

## Teardown / cost warning

```bash
make down
cd aws/terraform && terraform destroy   # if deployed
./aws/scripts/teardown.sh
```

Running RDS, ElastiCache, ALB, and ECS 24/7 can cost **$80–200+/month**. Tear down when not actively testing.

## Resume bullet templates

```text
Built a distributed URL shortening service with Redis cache-aside redirects, PostgreSQL persistence, async click analytics, and per-IP rate limiting, reducing repeat redirect latency by ___% under load.
```

```text
Designed a FastAPI + PostgreSQL + Redis architecture with async click-event workers, structured observability (/health, /metrics), and Docker Compose benchmarks measuring ___ req/sec sustained redirect throughput.
```

```text
Deployed containerized API and analytics worker services on AWS ECS with ALB ingress, RDS PostgreSQL, ElastiCache Redis, and CloudWatch alarms for 5xx errors, high latency, and worker failures.
```

## Makefile targets

| Command | Description |
|---------|-------------|
| `make setup` | Create venv and install dependencies |
| `make test` | Run pytest |
| `make up` | Start Docker Compose stack |
| `make down` | Stop stack |
| `make logs` | Tail container logs |
| `make generate-urls` | Bulk-create URLs for load tests |
| `make benchmark` | Run redirect latency benchmark |

## Project structure

```text
app/
  api/           FastAPI routes and middleware
  core/          config, database, logging, metrics
  models/        SQLModel tables (urls, click_events)
  schemas/       Pydantic request/response models
  services/      cache, queue, rate limiter, URL logic
  workers/       analytics worker process
scripts/         generate_urls, benchmark_redirects, load_test_hey
tests/           pytest suite
aws/             Terraform + deploy scripts
.github/         CI/CD workflows
results/         metrics template and benchmark output
```

## License

MIT
