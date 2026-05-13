from __future__ import annotations

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, set_auth_cookies
from app.auth.jwt import decode_token
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService


DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[redis.Redis, Depends(get_redis)]


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix) :]
    return None


async def get_optional_current_user(
    request: Request,
    response: Response,
    db: DbDep,
    redis_client: RedisDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    access_token = _extract_bearer_token(authorization) or request.cookies.get(ACCESS_COOKIE_NAME)
    if access_token:
        try:
            payload = decode_token(access_token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            user = await AuthService.get_user_by_id(db, int(payload["sub"]))
            if user:
                return user
        except (JWTError, HTTPException, ValueError):
            pass

    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            token_bundle = await AuthService.refresh_session(db=db, redis_client=redis_client, refresh_token=refresh_token)
            set_auth_cookies(response, token_bundle.access_token, token_bundle.refresh_token)
            return token_bundle.user
        except HTTPException:
            return None
    return None


def get_current_user(user: Annotated[User | None, Depends(get_optional_current_user)]) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
