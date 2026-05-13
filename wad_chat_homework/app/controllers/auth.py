from __future__ import annotations

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.config.settings import get_settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService
from app.templates import render_template


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.get("/register")
async def register_page(request: Request, user: User | None = Depends(get_optional_current_user)):
    if user:
        return RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "auth/register.html", {"error": None, "form": {}}, user)


@router.post("/register")
async def register_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    try:
        register_data = RegisterRequest(login=login, password=password, display_name=display_name or None)
        token_bundle = await AuthService.register_with_tokens(db, redis_client, register_data)
        response = RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
        set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
        return response
    except Exception as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else "Registration failed."
        return render_template(
            request,
            "auth/register.html",
            {"error": detail, "form": {"login": login, "display_name": display_name}},
        )


@router.get("/login")
async def login_page(request: Request, user: User | None = Depends(get_optional_current_user)):
    if user:
        return RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "auth/login.html", {"error": None, "form": {}}, user)


@router.post("/login")
async def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    try:
        login_data = LoginRequest(login=login, password=password)
        token_bundle = await AuthService.login_with_tokens(db, redis_client, login_data)
        response = RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
        set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
        return response
    except Exception as exc:
        detail = exc.detail if isinstance(exc, HTTPException) else "Login failed."
        return render_template(
            request,
            "auth/login.html",
            {"error": detail, "form": {"login": login}},
        )


@router.post("/logout")
async def logout(
    request: Request,
    redis_client: redis.Redis = Depends(get_redis),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    await AuthService.logout(redis_client, refresh_token)
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookies(response)
    return response


@router.get("/github/login")
async def github_login(request: Request):
    return await OAuthService.github_authorize_redirect(request)


@router.get("/github/callback", name="github_callback")
async def github_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    token_bundle = await OAuthService.github_callback(request, db, redis_client)
    response = RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token cookie is missing.")

    token_bundle = await AuthService.refresh_session(db=db, redis_client=redis_client, refresh_token=refresh_token)
    set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
    return TokenResponse(
        access_token=token_bundle.access_token,
        refresh_token=token_bundle.refresh_token,
        access_expires_in_minutes=settings.access_token_expire_minutes,
        refresh_expires_in_days=settings.refresh_token_expire_days,
    )


@router.get("/me", response_model=UserResponse)
async def auth_me(current_user: User = Depends(get_current_user)):
    return current_user
