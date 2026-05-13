from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config.settings import get_settings
from app.models.user import User


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
settings = get_settings()


def render_template(
    request: Request,
    template_name: str,
    context: dict[str, Any] | None = None,
    current_user: User | None = None,
    status_code: int = 200,
):
    base_context = {
        "request": request,
        "current_user": current_user,
        "github_enabled": settings.github_enabled,
    }
    if context:
        base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)
