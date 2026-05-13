from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config.settings import get_settings
from app.controllers.api import router as api_router
from app.controllers.auth import router as auth_router
from app.controllers.health import router as health_router
from app.controllers.web import router as web_router
from app.services.llm_service import LLMService
from app.services.oauth_service import configure_oauth


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    LLMService.validate_or_raise()
    if settings.llm_preload_on_startup:
        LLMService.preload()
    configure_oauth()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(health_router)
