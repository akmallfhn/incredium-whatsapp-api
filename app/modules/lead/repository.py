from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.entity import User, UserAccess
from app.modules.tenant.entity import STATUS_ACTIVE
from app.modules.whatsapp.entity import WaConversation, WaLead, WaLeadStage


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def conversation(self, conv_id: str) -> WaConversation | None:
        return await self._session.get(WaConversation, conv_id)

    async def lead(self, conv_id: str) -> WaLead | None:
        return await self._session.scalar(
            select(WaLead).where(WaLead.conv_id == conv_id).with_for_update()
        )

    async def find(self, conv_id: str) -> WaLead | None:
        return await self._session.get(WaLead, conv_id)

    async def stage(self, tenant_id: str, stage_id: str) -> WaLeadStage | None:
        return await self._session.scalar(
            select(WaLeadStage).where(
                WaLeadStage.tenant_id == tenant_id,
                WaLeadStage.id == stage_id,
                WaLeadStage.status == STATUS_ACTIVE,
            )
        )

    async def stage_by_id(self, tenant_id: str, stage_id: str) -> WaLeadStage | None:
        return await self._session.scalar(
            select(WaLeadStage).where(
                WaLeadStage.tenant_id == tenant_id,
                WaLeadStage.id == stage_id,
            )
        )

    async def stages(self, tenant_id: str, limit: int, skip: int) -> tuple[int, list[WaLeadStage]]:
        condition = (WaLeadStage.tenant_id == tenant_id, WaLeadStage.status == STATUS_ACTIVE)
        total = await self._session.scalar(
            select(func.count()).select_from(WaLeadStage).where(*condition)
        )
        rows = await self._session.scalars(
            select(WaLeadStage)
            .where(*condition)
            .order_by(WaLeadStage.position, WaLeadStage.id)
            .limit(limit)
            .offset(skip)
        )
        return total or 0, list(rows)

    async def handler(self, tenant_id: str, user_id: str) -> User | None:
        return await self._session.scalar(
            select(User)
            .join(UserAccess, UserAccess.user_id == User.id)
            .where(
                User.id == user_id,
                User.status == STATUS_ACTIVE,
                UserAccess.tenant_id == tenant_id,
            )
        )
