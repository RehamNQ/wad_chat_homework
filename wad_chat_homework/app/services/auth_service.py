from __future__ import annotations

import json
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.security import hash_password, verify_password
from app.config.settings import get_settings
from app.models.oauth_identity import OAuthIdentity
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


settings = get_settings()


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    @staticmethod
    def validate_login(login: str) -> str:
        normalized = login.strip()
        if len(normalized) < 3:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login must be at least 3 characters.")
        if len(normalized) > 50:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login is too long.")
        return normalized

    @staticmethod
    def validate_password(password: str) -> str:
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters.",
            )
        return password

    @staticmethod
    async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
        result = await db.execute(select(User).where(User.login == login))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        return await db.get(User, user_id)

    @staticmethod
    async def register_user(db: AsyncSession, login: str, password: str, display_name: str | None = None) -> User:
        login = AuthService.validate_login(login)
        password = AuthService.validate_password(password)

        existing = await AuthService.get_user_by_login(db, login)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login is already taken.")

        user = User(
            login=login,
            password_hash=hash_password(password),
            display_name=display_name.strip() if display_name else None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def register_with_tokens(
        db: AsyncSession,
        redis_client: redis.Redis,
        register_data: RegisterRequest,
    ) -> TokenBundle:
        user = await AuthService.register_user(
            db,
            register_data.login,
            register_data.password,
            register_data.display_name,
        )
        return await AuthService.issue_tokens(redis_client, user)

    @staticmethod
    async def authenticate_user(db: AsyncSession, login: str, password: str) -> User:
        login = AuthService.validate_login(login)
        password = AuthService.validate_password(password)

        user = await AuthService.get_user_by_login(db, login)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password.")
        return user

    @staticmethod
    async def login_with_tokens(
        db: AsyncSession,
        redis_client: redis.Redis,
        login_data: LoginRequest,
    ) -> TokenBundle:
        user = await AuthService.authenticate_user(db, login_data.login, login_data.password)
        return await AuthService.issue_tokens(redis_client, user)

    @staticmethod
    def _refresh_key(jti: str) -> str:
        return f"refresh_session:{jti}"

    @staticmethod
    async def issue_tokens(redis_client: redis.Redis, user: User) -> TokenBundle:
        access_token = create_access_token(user)
        refresh_token, jti = create_refresh_token(user)

        payload = {
            "user_id": user.id,
            "login": user.login,
        }
        ttl_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
        await redis_client.setex(AuthService._refresh_key(jti), ttl_seconds, json.dumps(payload))

        return TokenBundle(access_token=access_token, refresh_token=refresh_token, user=user)

    @staticmethod
    async def refresh_session(db: AsyncSession, redis_client: redis.Redis, refresh_token: str) -> TokenBundle:
        try:
            payload = decode_token(refresh_token)
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.") from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type.")

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing jti.")

        redis_key = AuthService._refresh_key(jti)
        session_data = await redis_client.get(redis_key)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session expired or revoked.",
            )

        stored_data = json.loads(session_data)
        if int(stored_data.get("user_id", -1)) != int(payload["sub"]):
            await redis_client.delete(redis_key)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session mismatch.")

        user = await AuthService.get_user_by_id(db, int(payload["sub"]))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

        await redis_client.delete(redis_key)
        return await AuthService.issue_tokens(redis_client, user)

    @staticmethod
    async def logout(redis_client: redis.Redis, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            return
        jti = payload.get("jti")
        if jti:
            await redis_client.delete(AuthService._refresh_key(jti))

    @staticmethod
    async def _next_available_login(db: AsyncSession, base_login: str) -> str:
        candidate = base_login[:50]
        index = 1
        while await AuthService.get_user_by_login(db, candidate):
            suffix = f"_{index}"
            candidate = f"{base_login[: max(1, 50 - len(suffix))]}{suffix}"
            index += 1
        return candidate

    @staticmethod
    async def get_or_create_github_user(
        db: AsyncSession,
        provider_user_id: str,
        provider_login: str,
        provider_email: str | None,
        display_name: str | None,
    ) -> User:
        result = await db.execute(
            select(OAuthIdentity)
            .options(selectinload(OAuthIdentity.user))
            .where(
                OAuthIdentity.provider == "github",
                OAuthIdentity.provider_user_id == provider_user_id,
            )
        )
        identity = result.scalar_one_or_none()
        if identity:
            return identity.user

        preferred_login = f"gh_{provider_login}".lower()
        unique_login = await AuthService._next_available_login(db, preferred_login)

        user = User(
            login=unique_login,
            password_hash=None,
            display_name=display_name or provider_login,
        )
        db.add(user)
        await db.flush()

        oauth_identity = OAuthIdentity(
            user_id=user.id,
            provider="github",
            provider_user_id=provider_user_id,
            provider_login=provider_login,
            provider_email=provider_email,
        )
        db.add(oauth_identity)
        await db.commit()
        await db.refresh(user)
        return user
