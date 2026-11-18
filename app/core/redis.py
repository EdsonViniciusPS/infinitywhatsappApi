"""Async Redis client lifecycle helpers."""

import redis.asyncio as redis

from app.core.config import get_settings


def create_redis_client() -> redis.Redis:
    """Create an async Redis client from configured URL."""
    settings = get_settings()
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
