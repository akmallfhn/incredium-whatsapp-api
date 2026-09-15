from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.entity import Token, User, UserAccess
from app.modules.tenant.entity import STATUS_ACTIVE


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_active_user_by_email(self, email: str) -> User | None:
        """Email dicocokkan case-insensitive; user nonaktif diperlakukan seperti tidak ada."""
        stmt = (
            select(User)
            .where(func.lower(User.email) == email.strip().lower(), User.status == STATUS_ACTIVE)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def find_active_user_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id, User.status == STATUS_ACTIVE).limit(1)
        return (await self._session.execute(stmt)).scalars().first()

    async def tenant_ids_for(self, user_id: str) -> list[str]:
        stmt = (
            select(UserAccess.tenant_id)
            .where(UserAccess.user_id == user_id)
            .order_by(UserAccess.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_token(self, *, user_id: str, token: str, expires_at: datetime) -> None:
        self._session.add(
            Token(user_id=user_id, token=token, expires_at=expires_at, is_active=True)
        )

    async def find_live_token(self, token: str, *, now: datetime) -> Token | None:
        stmt = (
            select(Token)
            .where(
                Token.token == token,
                Token.is_active.is_(True),
                Token.expires_at > now,
            )
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def delete_token(self, token: str) -> int:
        result = await self._session.execute(delete(Token).where(Token.token == token))
        return result.rowcount or 0

    async def delete_expired_tokens(self, *, now: datetime) -> int:
        result = await self._session.execute(delete(Token).where(Token.expires_at <= now))
        return result.rowcount or 0
