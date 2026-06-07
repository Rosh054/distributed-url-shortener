import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, metrics, redirect, urls
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

RESERVED_PATHS = frozenset({"/health", "/metrics", "/shorten", "/docs", "/redoc", "/openapi.json"})


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging(settings.log_level)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(urls.router)
app.include_router(redirect.router)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in RESERVED_PATHS or request.url.path.startswith("/urls/"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    limiter = get_rate_limiter()

    if not limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )

    return await call_next(request)
