from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as redis

from app.config.settings import get_settings


settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    yield redis_client
