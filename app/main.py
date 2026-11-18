"""FastAPI application entrypoint and lifespan management."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.redis import create_redis_client
from app.services.maintenance_service import periodic_maintenance_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage shared HTTP client, Redis, DB engine, and 7-day maintenance loop."""
    settings = get_settings()
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.EVOLUTION_TIMEOUT_SECONDS),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    app.state.redis = create_redis_client()
    app.state.maintenance_task = None
    if settings.MAINTENANCE_ENABLED:
        app.state.maintenance_task = asyncio.create_task(
            periodic_maintenance_loop(
                interval_seconds=settings.MAINTENANCE_INTERVAL_SECONDS,
                retention_days=settings.LOG_RETENTION_DAYS,
                backup_dir=Path(settings.BACKUP_DIR),
                redis_client=app.state.redis,
            )
        )
    try:
        yield
    finally:
        maintenance_task = getattr(app.state, "maintenance_task", None)
        if maintenance_task is not None:
            maintenance_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await maintenance_task
        await app.state.http_client.aclose()
        await app.state.redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_app()
