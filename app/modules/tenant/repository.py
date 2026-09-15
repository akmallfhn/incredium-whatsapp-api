from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenant.entity import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, tenant_id: str) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)
