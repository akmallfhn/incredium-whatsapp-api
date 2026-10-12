"""Antrean balasan satu baris per percakapan, aman saat webhook dikirim ulang."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.entity import Agent, AgentReplyJob
from app.modules.tenant.entity import STATUS_ACTIVE, Tenant
from app.modules.whatsapp.entity import MODE_AI, WaConversation, WaLead

DEBOUNCE_SECONDS = 2


@dataclass(frozen=True)
class ClaimedReply:
    conv_id: str
    generation: int
    latest_inbound_chat_id: str
    wa_phone_number_id: str


class AgentReplyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, *, conv_id: str, chat_id: str, wa_phone_number_id: str) -> None:
        due_at = func.current_timestamp() + text("INTERVAL '2 seconds'")
        stmt = pg_insert(AgentReplyJob).values(
            conv_id=conv_id,
            latest_inbound_chat_id=chat_id,
            wa_phone_number_id=wa_phone_number_id,
            due_at=due_at,
            status="pending",
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[AgentReplyJob.conv_id],
                set_={
                    "latest_inbound_chat_id": stmt.excluded.latest_inbound_chat_id,
                    "wa_phone_number_id": stmt.excluded.wa_phone_number_id,
                    "generation": AgentReplyJob.generation + 1,
                    "due_at": stmt.excluded.due_at,
                    "status": case(
                        (
                            AgentReplyJob.status.in_(("processing", "sending")),
                            AgentReplyJob.status,
                        ),
                        else_="pending",
                    ),
                    "attempts": case(
                        (AgentReplyJob.status.in_(("failed", "send_unknown")), 0),
                        else_=AgentReplyJob.attempts,
                    ),
                    "updated_at": func.current_timestamp(),
                },
            )
        )

    async def claim_due(self, limit: int, stuck_minutes: int) -> list[ClaimedReply]:
        stuck_before = datetime.now(timezone.utc) - timedelta(minutes=stuck_minutes)
        stmt = (
            select(AgentReplyJob)
            .where(
                or_(
                    and_(AgentReplyJob.status == "pending", AgentReplyJob.due_at <= func.now()),
                    and_(
                        AgentReplyJob.status == "processing",
                        AgentReplyJob.claimed_at < stuck_before,
                    ),
                )
            )
            .order_by(AgentReplyJob.due_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = "processing"
            row.claimed_generation = row.generation
            row.claimed_at = now
            row.attempts += 1
        await self._session.flush()
        return [
            ClaimedReply(
                row.conv_id, row.generation, row.latest_inbound_chat_id, row.wa_phone_number_id
            )
            for row in rows
        ]

    async def conversation(self, conv_id: str) -> WaConversation | None:
        return await self._session.get(WaConversation, conv_id)

    async def lock_for_echo(self, conv_id: str) -> None:
        await self._session.execute(
            select(WaLead.conv_id).where(WaLead.conv_id == conv_id).with_for_update()
        )
        await self._session.execute(
            select(AgentReplyJob.conv_id).where(AgentReplyJob.conv_id == conv_id).with_for_update()
        )

    async def mode(self, conv_id: str) -> str | None:
        return (
            await self._session.execute(select(WaLead.mode).where(WaLead.conv_id == conv_id))
        ).scalar_one_or_none()

    async def is_internal(self, conv_id: str) -> bool:
        value = (
            await self._session.execute(select(WaLead.is_internal).where(WaLead.conv_id == conv_id))
        ).scalar_one_or_none()
        return value is True

    async def active_config(self, tenant_id: str) -> dict | None:
        from app.modules.agents.entity import LlmModel

        stmt = (
            select(Agent, LlmModel)
            .join(Tenant, Tenant.active_agent_id == Agent.id)
            .join(LlmModel, LlmModel.id == Agent.model_id)
            .where(Tenant.id == tenant_id, Tenant.status == STATUS_ACTIVE)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        agent, model = row
        return {
            "agent_id": agent.id,
            "version": agent.config_version,
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "transfer_conditions": agent.transfer_conditions,
            "provider": model.provider,
            "api_model": model.api_model,
        }

    async def start_sending(self, job: ClaimedReply, *, agent_id: str, version: int) -> bool:
        authorized = (
            select(WaConversation.id)
            .join(Tenant, Tenant.id == WaConversation.tenant_id)
            .join(WaLead, WaLead.conv_id == WaConversation.id)
            .join(Agent, Agent.id == Tenant.active_agent_id)
            .where(
                WaConversation.id == job.conv_id,
                Tenant.status == STATUS_ACTIVE,
                Agent.id == agent_id,
                Agent.config_version == version,
                WaLead.mode == MODE_AI,
                WaLead.is_internal.is_(False),
            )
        )
        stmt = (
            update(AgentReplyJob)
            .where(
                AgentReplyJob.conv_id == job.conv_id,
                AgentReplyJob.status == "processing",
                AgentReplyJob.generation == job.generation,
                AgentReplyJob.claimed_generation == job.generation,
                AgentReplyJob.due_at <= func.now(),
                exists(authorized),
            )
            .values(status="sending", updated_at=func.current_timestamp())
            .returning(AgentReplyJob.conv_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def guard_send_locked(self, job: ClaimedReply, *, agent_id: str, version: int) -> bool:
        tenant_id = (
            await self._session.execute(
                select(WaConversation.tenant_id).where(WaConversation.id == job.conv_id)
            )
        ).scalar_one_or_none()
        if tenant_id is None:
            return False
        tenant = (
            (
                await self._session.execute(
                    select(Tenant).where(Tenant.id == tenant_id).with_for_update()
                )
            )
            .scalars()
            .first()
        )
        agent = (
            (
                await self._session.execute(
                    select(Agent).where(Agent.id == agent_id).with_for_update()
                )
            )
            .scalars()
            .first()
        )
        lead = (
            (
                await self._session.execute(
                    select(WaLead).where(WaLead.conv_id == job.conv_id).with_for_update()
                )
            )
            .scalars()
            .first()
        )
        reply = await self._session.get(AgentReplyJob, job.conv_id, with_for_update=True)
        return bool(
            tenant is not None
            and tenant.status == STATUS_ACTIVE
            and tenant.active_agent_id == agent_id
            and agent is not None
            and agent.config_version == version
            and lead is not None
            and lead.mode == MODE_AI
            and not lead.is_internal
            and reply is not None
            and reply.status == "sending"
            and reply.generation == job.generation
        )

    async def finish(self, job: ClaimedReply, *, unknown: bool = False) -> None:
        row = await self._session.get(AgentReplyJob, job.conv_id, with_for_update=True)
        if row is None:
            return
        if unknown:
            row.status = "send_unknown"
        else:
            row.status = "idle" if row.generation == job.generation else "pending"
        row.claimed_at = None
        row.claimed_generation = None

    async def retry(self, job: ClaimedReply, *, error: str, max_attempts: int) -> None:
        row = await self._session.get(AgentReplyJob, job.conv_id, with_for_update=True)
        if row is None:
            return
        row.status = "failed" if row.attempts >= max_attempts else "pending"
        row.error = error[:2000]
        row.claimed_at = None
        row.claimed_generation = None
        if row.status == "pending" and row.generation == job.generation:
            row.due_at = datetime.now(timezone.utc) + timedelta(seconds=10)

    async def requeue(self, job: ClaimedReply) -> None:
        row = await self._session.get(AgentReplyJob, job.conv_id, with_for_update=True)
        if row is None:
            return
        row.status = "pending"
        row.claimed_at = None
        row.claimed_generation = None
        if row.generation == job.generation:
            row.due_at = datetime.now(timezone.utc) + timedelta(seconds=DEBOUNCE_SECONDS)

    async def mark_unknown_stale(self, stuck_minutes: int) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=stuck_minutes)
        result = await self._session.execute(
            update(AgentReplyJob)
            .where(AgentReplyJob.status == "sending", AgentReplyJob.claimed_at < threshold)
            .values(
                status=case(
                    (AgentReplyJob.generation > AgentReplyJob.claimed_generation, "pending"),
                    else_="send_unknown",
                ),
                error="send result unknown after worker restart",
                claimed_at=None,
                claimed_generation=None,
            )
        )
        return result.rowcount or 0

    async def transfer(self, job: ClaimedReply, *, agent_id: str, version: int) -> bool:
        current = (
            select(AgentReplyJob.conv_id)
            .join(WaConversation, WaConversation.id == AgentReplyJob.conv_id)
            .join(Tenant, Tenant.id == WaConversation.tenant_id)
            .join(Agent, Agent.id == Tenant.active_agent_id)
            .where(
                AgentReplyJob.conv_id == job.conv_id,
                AgentReplyJob.status == "processing",
                AgentReplyJob.generation == job.generation,
                Agent.id == agent_id,
                Agent.config_version == version,
            )
        )
        result = await self._session.execute(
            update(WaLead)
            .where(WaLead.conv_id == job.conv_id, WaLead.mode == MODE_AI, exists(current))
            .values(mode="human", updated_at=func.current_timestamp())
        )
        return bool(result.rowcount)
