"""Login menerbitkan JWT dan mencatat sesinya; logout menghapus catatan itu."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.core.config import settings
from app.modules.auth.entity import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schema import LoginRequest
from app.shared.response import ApiError
from app.shared.security import decode_jwt, encode_jwt, hash_password, verify_password

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "invalid email or password"
INVALID_TOKEN = "missing or invalid authorization header"

# Hash palsu untuk email yang tidak ada, supaya waktu balasnya tidak membocorkan apa pun.
_DUMMY_HASH = hash_password(uuid.uuid4().hex)


class AuthService:
    def __init__(self, session: AsyncSession, *, repo: AuthRepository) -> None:
        self._session = session
        self._repo = repo

    async def login(self, req: LoginRequest) -> dict[str, Any]:
        if not settings.jwt_secret:
            logger.error("auth: JWT_SECRET is empty, refusing to issue tokens")
            raise ApiError(500, "an unexpected error occurred")

        user = await self._repo.find_active_user_by_email(req.email)
        # Password tetap dicek walau user tidak ada, supaya email terdaftar tak bisa ditebak.
        if not verify_password(req.password, user.password_hash if user else _DUMMY_HASH):
            raise ApiError(401, INVALID_CREDENTIALS)
        if user is None:
            raise ApiError(401, INVALID_CREDENTIALS)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=constants.JWT_TTL_DAYS)
        token = encode_jwt(
            {
                "sub": user.id,
                "email": user.email,
                "role": user.role,
                "jti": uuid.uuid4().hex,
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
            },
            settings.jwt_secret,
        )

        await self._repo.delete_expired_tokens(now=now)
        await self._repo.create_token(user_id=user.id, token=token, expires_at=expires_at)
        await self._session.commit()

        tenant_ids = await self._repo.tenant_ids_for(user.id)
        return {
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at.isoformat(),
            "user": _user_payload(user, tenant_ids),
        }

    async def logout(self, token: str) -> dict[str, Any]:
        user = await self.authenticate(token)
        await self._repo.delete_token(token)
        await self._session.commit()
        return {"id": user["id"], "email": user["email"]}

    async def authenticate(self, token: str) -> dict[str, Any]:
        """Tanda tangan sah saja belum cukup: barisnya harus masih ada supaya logout berarti."""
        if not settings.jwt_secret:
            raise ApiError(500, "an unexpected error occurred")

        claims = decode_jwt(token, settings.jwt_secret)
        if claims is None:
            raise ApiError(401, INVALID_TOKEN)

        now = datetime.now(timezone.utc)
        if await self._repo.find_live_token(token, now=now) is None:
            raise ApiError(401, INVALID_TOKEN)

        user = await self._repo.find_active_user_by_id(claims.get("sub", ""))
        if user is None:
            raise ApiError(401, INVALID_TOKEN)

        tenant_ids = await self._repo.tenant_ids_for(user.id)
        return _user_payload(user, tenant_ids)


def _user_payload(user: User, tenant_ids: list[str]) -> dict[str, Any]:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "avatar": user.avatar,
        "role": user.role,
        "status": user.status,
        "tenant_ids": tenant_ids,
    }
