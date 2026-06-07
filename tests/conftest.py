import os
from contextlib import contextmanager

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["RATE_LIMIT_REQUESTS"] = "5"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"

from app import core  # noqa: E402
from app.api.main import app  # noqa: E402
from app.core.database import get_session  # noqa: E402
from app.models.click_event import ClickEvent  # noqa: F401,E402
from app.models.url import Url  # noqa: F401,E402
from app.services.cache import UrlCache  # noqa: E402
from app.services.click_queue import ClickQueue  # noqa: E402
from app.services.rate_limiter import RateLimiter  # noqa: E402
from app.workers.main import AnalyticsWorker  # noqa: E402


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    core.database.engine = engine
    return engine


@pytest.fixture(autouse=True)
def patch_session_scope(engine):
    @contextmanager
    def _session_scope():
        with Session(engine) as session:
            yield session

    core.database.session_scope = _session_scope
    yield


@pytest.fixture(name="fake_redis")
def fake_redis_fixture():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture(name="cache")
def cache_fixture(fake_redis):
    return UrlCache(client=fake_redis)


@pytest.fixture(name="click_queue")
def click_queue_fixture(fake_redis):
    return ClickQueue(client=fake_redis)


@pytest.fixture(name="rate_limiter")
def rate_limiter_fixture(fake_redis):
    return RateLimiter(client=fake_redis)


@pytest.fixture(autouse=True)
def patch_rate_limiter(fake_redis):
    from app.services.rate_limiter import RateLimiter, reset_rate_limiter

    reset_rate_limiter(client=fake_redis)
    yield
    reset_rate_limiter()


@pytest.fixture(autouse=True)
def reset_metrics():
    from app.core.metrics import app_metrics

    app_metrics.redirect_count = 0
    app_metrics.cache_hit_count = 0
    app_metrics.cache_miss_count = 0
    app_metrics.total_redirect_latency_ms = 0.0
    app_metrics.urls_created_count = 0
    app_metrics.rate_limited_count = 0
    yield


@pytest.fixture(name="client")
def client_fixture(engine, cache, click_queue):
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    from app.api.routes import health, redirect, urls

    app.dependency_overrides[health.get_cache] = lambda: cache
    app.dependency_overrides[health.get_click_queue] = lambda: click_queue
    app.dependency_overrides[urls.get_cache] = lambda: cache
    app.dependency_overrides[urls.get_click_queue] = lambda: click_queue
    app.dependency_overrides[redirect.get_cache] = lambda: cache
    app.dependency_overrides[redirect.get_click_queue] = lambda: click_queue

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def worker(click_queue, engine):
    return AnalyticsWorker(worker_id="test-worker")
