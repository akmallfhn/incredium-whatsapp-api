from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.meta.entity import MetaApp, MetaConnection
from app.modules.tenant.entity import STATUS_ACTIVE, Tenant


@dataclass(frozen=True)
class ConnectionContext:
    """Semua yang dibutuhkan pemroses webhook untuk satu event, hasil satu kali query."""

    tenant_id: str
    tenant_slug: str
    phone_number_id: str
    access_token: str


class MetaAppRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_app_id(self, app_id: str) -> MetaApp | None:
        stmt = (
            select(MetaApp)
            .where(MetaApp.app_id == app_id, MetaApp.status == STATUS_ACTIVE)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalars().first()


class MetaConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_context_by_phone_number_id(
        self, phone_number_id: str
    ) -> ConnectionContext | None:
        """Routing multitenant: nomor tujuan di event Meta menentukan tenant dan token-nya."""
        stmt = (
            select(
                MetaConnection.tenant_id,
                Tenant.slug,
                MetaConnection.wa_phone_number_id,
                MetaConnection.access_token,
            )
            .join(Tenant, Tenant.id == MetaConnection.tenant_id)
            .where(
                MetaConnection.wa_phone_number_id == phone_number_id,
                MetaConnection.status == STATUS_ACTIVE,
                Tenant.status == STATUS_ACTIVE,
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return ConnectionContext(
            tenant_id=row.tenant_id,
            tenant_slug=row.slug or row.tenant_id,
            phone_number_id=row.wa_phone_number_id,
            access_token=row.access_token or "",
        )
