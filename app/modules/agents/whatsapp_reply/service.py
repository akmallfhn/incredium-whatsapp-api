"""Pekerja agent balasan yang menjalankan LangGraph di luar jalur webhook."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.db.session import session_scope
from app.modules.agents.repository import AgentRepository
from app.modules.agents.whatsapp_reply.graph import build_reply_graph
from app.modules.agents.whatsapp_reply.repository import AgentReplyRepository, ClaimedReply
from app.modules.meta.repository import MetaConnectionRepository
from app.modules.whatsapp.entity import DIRECTION_OUTBOUND, SENDER_TYPE_AGENT
from app.modules.whatsapp.meta_client import MetaMessageClient
from app.modules.whatsapp.repository import WaChatRepository
from app.shared.agent_cache import AgentCache

logger = logging.getLogger(__name__)
SWEEP_SECONDS = 0.5
STUCK_MINUTES = 5
MAX_ATTEMPTS = 5
BATCH_SIZE = 10
MAX_TEXT_LENGTH = 4096
CUSTOMER_WINDOW = timedelta(hours=24)


class AgentReplyWorker:
    def __init__(self, *, messages: MetaMessageClient, cache: AgentCache) -> None:
        self._messages = messages
        self._cache = cache
        self._graph = build_reply_graph()

    async def run_forever(self) -> None:
        while True:
            try:
                await self.sweep()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("agent reply: sweep gagal")
            await asyncio.sleep(SWEEP_SECONDS)

    async def sweep(self) -> int:
        async with session_scope() as session:
            repo = AgentReplyRepository(session)
            unknown = await repo.mark_unknown_stale(STUCK_MINUTES)
            jobs = await repo.claim_due(BATCH_SIZE, STUCK_MINUTES)
            await session.commit()
        if unknown:
            logger.warning("agent reply: %s kirim tidak diketahui hasilnya", unknown)
        await asyncio.gather(*(self._process(job) for job in jobs))
        return len(jobs)

    async def _process(self, job: ClaimedReply) -> None:
        sending = False
        try:
            context = await self._load(job)
            if context is None:
                await self._finish(job)
                return
            conv, config, transcript, knowledge, connection = context
            if not connection.access_token:
                raise RuntimeError("active WhatsApp connection has no access token")
            state = await self._graph.ainvoke(
                {
                    "provider": config["provider"],
                    "api_model": config["api_model"],
                    "name": config["name"],
                    "personality": config.get("personality"),
                    "system_prompt": config["system_prompt"],
                    "transfer_conditions": config["transfer_conditions"],
                    "transcript": transcript,
                    "knowledge": knowledge,
                }
            )
            if state.get("error"):
                raise RuntimeError(state["error"])
            decision = state.get("decision")
            if decision is None or decision.action == "skip":
                await self._finish(job)
                return
            if decision.action == "transfer":
                async with session_scope() as session:
                    repo = AgentReplyRepository(session)
                    transferred = await repo.transfer(
                        job, agent_id=config["agent_id"], version=config["version"]
                    )
                    if transferred:
                        await repo.finish(job)
                    else:
                        await repo.requeue(job)
                    await session.commit()
                if transferred:
                    await self._cache.delete_mode(job.conv_id)
                else:
                    await self._cache.delete_agent(conv.tenant_id)
                return
            body = decision.message.strip()[:MAX_TEXT_LENGTH]
            if not body:
                await self._finish(job)
                return
            async with session_scope() as session:
                repo = AgentReplyRepository(session)
                last_inbound_at = await WaChatRepository(session).last_inbound_at(job.conv_id)
                window_open = (
                    last_inbound_at is not None
                    and datetime.now(timezone.utc) - last_inbound_at < CUSTOMER_WINDOW
                )
                if not window_open:
                    await repo.finish(job)
                    await session.commit()
                    return
                started = window_open and await repo.start_sending(
                    job, agent_id=config["agent_id"], version=config["version"]
                )
                if not started:
                    await repo.requeue(job)
                await session.commit()
            if not started:
                await self._cache.delete_agent(conv.tenant_id)
                return
            async with session_scope() as session:
                repo = AgentReplyRepository(session)
                if not await repo.guard_send_locked(
                    job, agent_id=config["agent_id"], version=config["version"]
                ):
                    await repo.finish(job)
                    await session.commit()
                    return
                sending = True
                wam_id = await self._messages.send_text(
                    access_token=connection.access_token,
                    phone_number_id=connection.phone_number_id,
                    to=conv.phone_number,
                    body=body,
                )
                await WaChatRepository(session).upsert_message(
                    conv_id=job.conv_id,
                    wam_id=wam_id,
                    direction=DIRECTION_OUTBOUND,
                    sender_type=SENDER_TYPE_AGENT,
                    msg_type="text",
                    message=body,
                    agent_id=config["agent_id"],
                    sent_at=datetime.now(timezone.utc),
                )
                await repo.finish(job)
                await session.commit()
        except Exception as exc:
            logger.exception("agent reply: gagal memproses conv_id=%s", job.conv_id)
            try:
                async with session_scope() as session:
                    repo = AgentReplyRepository(session)
                    if sending:
                        await repo.finish(job, unknown=True)
                    else:
                        await repo.retry(
                            job, error=f"{type(exc).__name__}: {exc}", max_attempts=MAX_ATTEMPTS
                        )
                    await session.commit()
            except Exception:
                logger.exception("agent reply: gagal mencatat error conv_id=%s", job.conv_id)

    async def _load(self, job: ClaimedReply):
        async with session_scope() as session:
            repo = AgentReplyRepository(session)
            conv = await repo.conversation(job.conv_id)
            if conv is None or await repo.is_internal(job.conv_id):
                return None
            config = await self._cache.get_agent(conv.tenant_id)
            if config is None:
                config = await repo.active_config(conv.tenant_id)
                if config is None:
                    return None
                await self._cache.set_agent(conv.tenant_id, config)
            if not await self._cache.get_ai_mode(job.conv_id):
                if await repo.mode(job.conv_id) != "ai":
                    return None
                await self._cache.set_ai_mode(job.conv_id)
            connection = await MetaConnectionRepository(session).find_context_by_phone_number_id(
                job.wa_phone_number_id
            )
            if connection is None or connection.tenant_id != conv.tenant_id:
                raise RuntimeError("WhatsApp connection not active for conversation tenant")
            chats = await WaChatRepository(session).list_by_conversation(
                conv_id=job.conv_id, limit=30, skip=0
            )
            transcript = "\n".join(
                f"{'Pelanggan' if chat.direction == 'inbound' else 'Tim'}: "
                f"{chat.message or '[' + chat.type + ']'}"
                for chat in reversed(chats)
            )[-8000:]
            sources = await AgentRepository(session).active_sources(config["agent_id"])
            knowledge = "\n\n".join(f"{row.title}: {row.content}" for row in sources)[:6000]
            return conv, config, transcript, knowledge, connection

    async def _finish(self, job: ClaimedReply) -> None:
        async with session_scope() as session:
            await AgentReplyRepository(session).finish(job)
            await session.commit()
