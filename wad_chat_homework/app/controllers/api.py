from __future__ import annotations

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.auth.dependencies import get_current_user
from app.config.settings import get_settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.chat import ChatCreateRequest, ChatResponse
from app.schemas.message import MessageCreateRequest, MessageResponse
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService


router = APIRouter(prefix="/api", tags=["api"])
settings = get_settings()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def api_register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.register_user(db, payload.login, payload.password, payload.display_name)


@router.post("/auth/login", response_model=TokenResponse)
async def api_login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    token_bundle = await AuthService.login_with_tokens(db, redis_client, payload)
    set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
    return TokenResponse(
        access_token=token_bundle.access_token,
        refresh_token=token_bundle.refresh_token,
        access_expires_in_minutes=settings.access_token_expire_minutes,
        refresh_expires_in_days=settings.refresh_token_expire_days,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def api_logout(
    request: Request,
    response: Response,
    redis_client: redis.Redis = Depends(get_redis),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    await AuthService.logout(redis_client, refresh_token)
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def api_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/chats", response_model=list[ChatResponse])
async def api_list_chats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await ChatService.list_chats_for_user(db, current_user)


@router.post("/chats", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def api_create_chat(
    payload: ChatCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ChatService.create_chat(db, current_user, payload.title)


@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def api_get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ChatService.get_user_chat_or_404(db, current_user, chat_id)


@router.post("/chats/{chat_id}/messages", response_model=list[MessageResponse], status_code=status.HTTP_201_CREATED)
async def api_send_message(
    chat_id: int,
    payload: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ChatService.send_message_api_response(db, current_user, chat_id, payload.content)
