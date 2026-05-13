from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.config.settings import get_settings
from app.db.redis import redis_client


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live_check():
    return {"status": "ok"}


@router.get("/ready")
async def ready_check():
    settings = get_settings()
    model_exists = Path(settings.model_path).expanduser().is_file()
    redis_ok = False
    try:
        redis_ok = bool(await redis_client.ping())
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if model_exists and redis_ok else "degraded",
        "model_path": settings.model_path,
        "model_exists": model_exists,
        "redis_ok": redis_ok,
    }
