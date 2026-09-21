from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.whatsapp.entity import (
    DIRECTION_OUTBOUND,
    SENDER_TYPE_ADMIN,
    WaChat,
    WaConversation,
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
