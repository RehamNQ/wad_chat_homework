from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt

from app.config.settings import get_settings
from app.models.user import User


settings = get_settings()
ALGORITHM = "HS256"


def _build_base_claims(user: User, token_type: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user.id),
        "login": user.login,
        "type": token_type,
        "iat": int(now.timestamp()),
    }


def create_access_token(user: User) -> str:
    claims = _build_base_claims(user, "access")
    claims["exp"] = int(
        (datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
    )
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user: User) -> tuple[str, str]:
    claims = _build_base_claims(user, "refresh")
    jti = str(uuid4())
    claims["jti"] = jti
    claims["exp"] = int(
        (datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)).timestamp()
    )
    token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def decode_token_or_none(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return decode_token(token)
    except JWTError:
        return None
