from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, delete, func, literal_column, or_, select, true, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.tenant.entity import STATUS_ACTIVE
from app.modules.whatsapp.entity import (
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    EVENT_STATUS_DONE,
    EVENT_STATUS_FAILED,
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_PENDING,
    EVENT_STATUS_PROCESSING,
    SENDER_TYPE_ADMIN,
    WaChat,
    WaConversation,
    WaLead,
    WaLeadStage,
    WaWebhookEvent,
)

LIKE_ESCAPE = "\\"


@dataclass(frozen=True)
class ConversationFilter:
    tenant_id: str
    search: str | None = None
    stage_id: str | None = None
    mode: str | None = None
    # False berarti handler tidak difilter; True dengan handler_id None berarti belum ada handler.
    by_handler: bool = False
    handler_id: str | None = None


@dataclass(frozen=True)
class ConversationRow:
    conversation: WaConversation
    last_chat: WaChat | None
    last_inbound_at: datetime | None
    unread_count: int


def _conversation_clauses(f: ConversationFilter) -> list[Any]:
    """Filter daftar percakapan; query pemakainya wajib LEFT JOIN wa_leads."""
    clauses: list[Any] = [WaConversation.tenant_id == f.tenant_id]
    if f.stage_id is not None:
        clauses.append(WaLead.stage_id == f.stage_id)
    if f.mode is not None:
        clauses.append(WaLead.mode == f.mode)
    if f.by_handler:
        clauses.append(
            WaLead.handler_id.is_(None)
            if f.handler_id is None
            else WaLead.handler_id == f.handler_id
        )
    if f.search:
        escaped = f.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        clauses.append(
            or_(
                WaConversation.full_name.ilike(pattern, escape=LIKE_ESCAPE),
                WaConversation.phone_number.ilike(pattern, escape=LIKE_ESCAPE),
                WaLead.brand_name.ilike(pattern, escape=LIKE_ESCAPE),
                select(WaChat.id)
                .where(
                    WaChat.conv_id == WaConversation.id,
                    WaChat.message.ilike(pattern, escape=LIKE_ESCAPE),
                )
                .exists(),
            )
        )
    return clauses


class WaConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, conv_id: str) -> WaConversation | None:
        return await self._session.get(WaConversation, conv_id)

    async def count_filtered(self, f: ConversationFilter) -> int:
        stmt = (
            select(func.count())
            .select_from(WaConversation)
            .outerjoin(WaLead, WaLead.conv_id == WaConversation.id)
            .where(*_conversation_clauses(f))
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def list_filtered(
        self, f: ConversationFilter, *, limit: int, skip: int
    ) -> list[ConversationRow]:
        # LATERAL supaya chat terakhir dibaca dari index (conv_id, created_at DESC).
        last_chat = (
            select(WaChat)
            .where(WaChat.conv_id == WaConversation.id)
            .order_by(WaChat.created_at.desc(), WaChat.id.desc())
            .limit(1)
            .lateral("last_chat")
        )
        last = aliased(WaChat, last_chat)
        read_chat = aliased(WaChat)
        last_inbound_at = (
            select(func.max(WaChat.created_at))
            .where(WaChat.conv_id == WaConversation.id, WaChat.direction == DIRECTION_INBOUND)
            .correlate(WaConversation)
            .scalar_subquery()
        )
        unread_count = (
            select(func.count())
            .select_from(WaChat)
            .where(
                WaChat.conv_id == WaConversation.id,
                WaChat.direction == DIRECTION_INBOUND,
                or_(read_chat.id.is_(None), WaChat.created_at > read_chat.created_at),
            )
            .correlate(WaConversation, read_chat)
            .scalar_subquery()
        )
        stmt = (
            select(WaConversation, last, last_inbound_at, unread_count)
            .outerjoin(WaLead, WaLead.conv_id == WaConversation.id)
            .outerjoin(read_chat, read_chat.id == WaConversation.last_read_id)
            .outerjoin(last, true())
            .where(*_conversation_clauses(f))
            .order_by(WaConversation.created_at.desc(), WaConversation.id.desc())
            .limit(limit)
            .offset(skip)
        )
        return [
            ConversationRow(conv, chat, inbound_at, unread)
            for conv, chat, inbound_at, unread in (await self._session.execute(stmt)).all()
        ]

    async def mark_as_read(self, conv_id: str) -> str | None:
        """Tandai sampai chat terbaru; percakapan tanpa chat tetap null."""
        latest = (
            select(WaChat.id)
            .where(WaChat.conv_id == conv_id)
            .order_by(WaChat.created_at.desc(), WaChat.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            update(WaConversation)
            .where(WaConversation.id == conv_id)
            .values(last_read_id=latest)
            .returning(WaConversation.last_read_id)
            .execution_options(synchronize_session=False)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_or_create(
        self, *, tenant_id: str, full_name: str, phone_number: str
    ) -> WaConversation:
        """Upsert; sandarkan ke unique (tenant_id, phone_number) karena event Meta bisa balapan."""
        stmt = (
            pg_insert(WaConversation)
            .values(tenant_id=tenant_id, full_name=full_name, phone_number=phone_number)
            .on_conflict_do_update(
                index_elements=[WaConversation.tenant_id, WaConversation.phone_number],
                set_={
                    "full_name": func.coalesce(
                        func.nullif(pg_insert(WaConversation).excluded.full_name, ""),
                        WaConversation.full_name,
                    )
                },
            )
            .returning(WaConversation)
        )
        result = await self._session.execute(stmt, execution_options={"populate_existing": True})
        conv = result.scalars().one()
        await self._ensure_lead(conv_id=conv.id, tenant_id=tenant_id)
        return conv

    async def _ensure_lead(self, *, conv_id: str, tenant_id: str) -> None:
        """Baris wa_leads mulai di stage pertama tenant; DO NOTHING supaya aman saat replay."""
        first_stage = (
            select(WaLeadStage.id)
            .where(WaLeadStage.tenant_id == tenant_id, WaLeadStage.status == STATUS_ACTIVE)
            .order_by(WaLeadStage.position)
            .limit(1)
            .scalar_subquery()
        )
        await self._session.execute(
            pg_insert(WaLead)
            .values(conv_id=conv_id, stage_id=first_stage)
            .on_conflict_do_nothing(index_elements=[WaLead.conv_id])
        )


class WaChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_by_conversation(self, conv_id: str) -> int:
        stmt = select(func.count()).select_from(WaChat).where(WaChat.conv_id == conv_id)
        return (await self._session.execute(stmt)).scalar_one()

    async def list_by_conversation(self, *, conv_id: str, limit: int, skip: int) -> list[WaChat]:
        stmt = (
            select(WaChat)
            .where(WaChat.conv_id == conv_id)
            .order_by(WaChat.created_at, WaChat.id)
            .limit(limit)
            .offset(skip)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_in_conversation(self, *, chat_id: str, conv_id: str) -> WaChat | None:
        stmt = select(WaChat).where(WaChat.id == chat_id, WaChat.conv_id == conv_id).limit(1)
        return (await self._session.execute(stmt)).scalars().first()

    async def last_inbound_at(self, conv_id: str) -> datetime | None:
        stmt = select(func.max(WaChat.created_at)).where(
            WaChat.conv_id == conv_id, WaChat.direction == DIRECTION_INBOUND
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def find_by_wam_id(self, wam_id: str, conv_id: str | None = None) -> WaChat | None:
        stmt = select(WaChat).where(WaChat.wam_id == wam_id)
        if conv_id is not None:
            stmt = stmt.where(WaChat.conv_id == conv_id)
        return (await self._session.execute(stmt.limit(1))).scalars().first()

    async def find_storage_url_by_sha256(self, *, tenant_id: str, sha256: str) -> str | None:
        """URL file yang isinya sama di tenant ini; ekspresinya harus persis index parsialnya."""
        sha_expr = WaChat.attachment.op("->>")(literal_column("'sha256'"))
        url_expr = WaChat.attachment.op("->>")(literal_column("'storage_url'"))
        stmt = (
            select(url_expr)
            .join(WaConversation, WaConversation.id == WaChat.conv_id)
            .where(
                sha_expr == sha256,
                url_expr.is_not(None),
                WaConversation.tenant_id == tenant_id,
            )
            .order_by(WaChat.created_at)
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def upsert_message(
        self,
        *,
        conv_id: str,
        wam_id: str,
        direction: str,
        sender_type: str,
        msg_type: str,
        message: str,
        attachment: Any | None = None,
        reply_to_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """Isi pesan menang atas baris penampung yang dibuat status; kolom status tidak disentuh."""
        values: dict[str, Any] = {
            "conv_id": conv_id,
            "wam_id": wam_id,
            "direction": direction,
            "sender_type": sender_type,
            "type": msg_type,
            "message": message,
            "attachment": attachment,
            "reply_to_id": reply_to_id,
        }
        if created_at is not None:
            values["created_at"] = created_at

        stmt = pg_insert(WaChat).values(**values)
        # conv_id sengaja tidak ikut ditimpa supaya pesan tidak pindah percakapan.
        set_: dict[str, Any] = {
            col: stmt.excluded[col]
            for col in ("direction", "sender_type", "type", "message", "attachment", "reply_to_id")
        }
        if created_at is not None:
            set_["created_at"] = stmt.excluded.created_at
        set_["updated_at"] = func.current_timestamp()

        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=[WaChat.wam_id], set_=set_)
        )

    async def upsert_status(
        self,
        *,
        conv_id: str,
        wam_id: str,
        status: str,
        timestamp_field: str,
        occurred_at: datetime,
    ) -> None:
        """Status untuk pesan yang belum tercatat; echo yang menyusul mengisi baris yang sama."""
        stmt = pg_insert(WaChat).values(
            conv_id=conv_id,
            wam_id=wam_id,
            direction=DIRECTION_OUTBOUND,
            sender_type=SENDER_TYPE_ADMIN,
            type="text",
            message="",
            status=status,
            created_at=occurred_at,
            **{timestamp_field: occurred_at},
        )
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=[WaChat.wam_id],
                set_={
                    "status": stmt.excluded.status,
                    timestamp_field: stmt.excluded[timestamp_field],
                    "updated_at": func.current_timestamp(),
                },
            )
        )


class WaWebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, *, app_id: str, payload: Any) -> str:
        """Catat event apa adanya. Dipanggil sebelum 200 dibalas ke Meta, jadi harus murah."""
        stmt = (
            pg_insert(WaWebhookEvent)
            .values(app_id=app_id, payload=payload)
            .returning(WaWebhookEvent.id)
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def claim_one(self, *, event_id: str, max_attempts: int) -> WaWebhookEvent | None:
        """Ambil satu event yang masih pending; None kalau sudah diambil pihak lain."""
        stmt = (
            update(WaWebhookEvent)
            .where(
                WaWebhookEvent.id == event_id,
                WaWebhookEvent.status == EVENT_STATUS_PENDING,
                WaWebhookEvent.attempts < max_attempts,
            )
            .values(
                status=EVENT_STATUS_PROCESSING,
                claimed_at=func.current_timestamp(),
                attempts=WaWebhookEvent.attempts + 1,
            )
            .returning(WaWebhookEvent)
            .execution_options(synchronize_session=False)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def claim_batch(
        self, *, limit: int, max_attempts: int, stuck_before: datetime
    ) -> list[WaWebhookEvent]:
        """Event tertunda plus yang macet karena prosesnya mati; SKIP LOCKED memisah replika."""
        ids = (
            (
                await self._session.execute(
                    select(WaWebhookEvent.id)
                    .where(
                        WaWebhookEvent.attempts < max_attempts,
                        or_(
                            WaWebhookEvent.status == EVENT_STATUS_PENDING,
                            and_(
                                WaWebhookEvent.status == EVENT_STATUS_PROCESSING,
                                WaWebhookEvent.claimed_at < stuck_before,
                            ),
                        ),
                    )
                    .order_by(WaWebhookEvent.received_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        if not ids:
            return []

        stmt = (
            update(WaWebhookEvent)
            .where(WaWebhookEvent.id.in_(ids))
            .values(
                status=EVENT_STATUS_PROCESSING,
                claimed_at=func.current_timestamp(),
                attempts=WaWebhookEvent.attempts + 1,
            )
            .returning(WaWebhookEvent)
            .execution_options(synchronize_session=False)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_done(self, event_id: str) -> None:
        await self._session.execute(
            update(WaWebhookEvent)
            .where(WaWebhookEvent.id == event_id)
            .values(
                status=EVENT_STATUS_DONE,
                processed_at=func.current_timestamp(),
                error=None,
            )
            .execution_options(synchronize_session=False)
        )

    async def mark_ignored(self, event_id: str) -> None:
        """Tersimpan tapi tidak ada yang dikerjakan; dibedakan dari done supaya bisa ditinjau."""
        await self._session.execute(
            update(WaWebhookEvent)
            .where(WaWebhookEvent.id == event_id)
            .values(status=EVENT_STATUS_IGNORED, processed_at=func.current_timestamp())
            .execution_options(synchronize_session=False)
        )

    async def mark_failed(self, *, event_id: str, error: str) -> None:
        """Gagal permanen: bentuk payload tidak dikenali, mengulang tidak akan mengubah apa pun."""
        await self._session.execute(
            update(WaWebhookEvent)
            .where(WaWebhookEvent.id == event_id)
            .values(
                status=EVENT_STATUS_FAILED,
                processed_at=func.current_timestamp(),
                error=error[:2000],
            )
            .execution_options(synchronize_session=False)
        )

    async def release(self, *, event_id: str, error: str, max_attempts: int) -> None:
        """Kembalikan ke pending supaya sweeper mencoba lagi; habis percobaan jadi failed."""
        status = case(
            (WaWebhookEvent.attempts >= max_attempts, EVENT_STATUS_FAILED),
            else_=EVENT_STATUS_PENDING,
        )
        await self._session.execute(
            update(WaWebhookEvent)
            .where(WaWebhookEvent.id == event_id)
            .values(status=status, claimed_at=None, error=error[:2000])
            .execution_options(synchronize_session=False)
        )

    async def prune_done(self, *, processed_before: datetime) -> int:
        """Buang event lama yang sudah selesai; yang failed disisakan untuk diperiksa."""
        result = await self._session.execute(
            delete(WaWebhookEvent).where(
                WaWebhookEvent.status == EVENT_STATUS_DONE,
                WaWebhookEvent.processed_at < processed_before,
            )
        )
        return result.rowcount or 0

    async def backlog(self) -> tuple[datetime | None, int]:
        """Event terakhir masuk dan jumlah yang belum selesai; dasar pemantauan webhook."""
        row = (
            await self._session.execute(
                select(
                    func.max(WaWebhookEvent.received_at),
                    func.count().filter(
                        WaWebhookEvent.status.in_((EVENT_STATUS_PENDING, EVENT_STATUS_PROCESSING))
                    ),
                )
            )
        ).one()
        return row[0], row[1] or 0
