from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp.entity import (
    DIRECTION_OUTBOUND,
    EVENT_STATUS_DONE,
    EVENT_STATUS_FAILED,
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_PENDING,
    EVENT_STATUS_PROCESSING,
    SENDER_TYPE_ADMIN,
    WaChat,
    WaConversation,
    WaWebhookEvent,
)


class WaConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        return result.scalars().one()


class WaChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_wam_id(self, wam_id: str, conv_id: str | None = None) -> WaChat | None:
        stmt = select(WaChat).where(WaChat.wam_id == wam_id)
        if conv_id is not None:
            stmt = stmt.where(WaChat.conv_id == conv_id)
        return (await self._session.execute(stmt.limit(1))).scalars().first()

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
