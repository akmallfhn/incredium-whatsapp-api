from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.entity import UserAccess
from app.modules.tenant.entity import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, tenant_id: str) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def create(
        self, *, name: str, slug: str, image_url: str | None, legal_name: str | None
    ) -> Tenant | None:
        stmt = (
            insert(Tenant)
            .values(name=name, slug=slug, image_url=image_url, legal_name=legal_name)
            .on_conflict_do_nothing(index_elements=[Tenant.slug])
            .returning(Tenant)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    def grant_access(self, *, user_id: str, tenant_id: str) -> None:
        self._session.add(UserAccess(user_id=user_id, tenant_id=tenant_id))
