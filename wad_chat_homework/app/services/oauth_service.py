from __future__ import annotations

import redis.asyncio as redis
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.services.auth_service import AuthService, TokenBundle


settings = get_settings()
oauth = OAuth()


def configure_oauth() -> None:
    if not settings.github_enabled:
        return

    if oauth.create_client("github") is not None:
        return

    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )


class OAuthService:
    @staticmethod
    def _github_client():
        client = oauth.create_client("github")
        if client is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GitHub OAuth is not configured.")
        return client

    @staticmethod
    async def github_authorize_redirect(request: Request):
        client = OAuthService._github_client()
        redirect_uri = request.url_for("github_callback")
        return await client.authorize_redirect(request, redirect_uri)

    @staticmethod
    async def github_callback(
        request: Request,
        db: AsyncSession,
        redis_client: redis.Redis,
    ) -> TokenBundle:
        client = OAuthService._github_client()
        token = await client.authorize_access_token(request)
        profile_response = await client.get("user", token=token)
        profile = profile_response.json()

        provider_email = None
        emails_response = await client.get("user/emails", token=token)
        if emails_response.is_success:
            emails = emails_response.json()
            primary = next((item for item in emails if item.get("primary")), None)
            if primary:
                provider_email = primary.get("email")
            elif emails:
                provider_email = emails[0].get("email")

        provider_user_id = str(profile["id"])
        provider_login = profile["login"]
        display_name = profile.get("name") or provider_login

        user = await AuthService.get_or_create_github_user(
            db=db,
            provider_user_id=provider_user_id,
            provider_login=provider_login,
            provider_email=provider_email,
            display_name=display_name,
        )
        return await AuthService.issue_tokens(redis_client, user)
