"""Pemroses event webhook dari Postgres; sumbernya baris wa_webhook_events, bukan request HTTP."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.db.session import session_scope
from app.modules.whatsapp.entity import WaWebhookEvent
from app.modules.whatsapp.repository import WaWebhookEventRepository
from app.modules.whatsapp.schema import WAWebhookBody
from app.modules.whatsapp.service import WhatsAppWebhookService

logger = logging.getLogger(__name__)

ServiceFactory = Callable[[AsyncSession], WhatsAppWebhookService]
EventsFactory = Callable[[AsyncSession], WaWebhookEventRepository]

# Jarak antar pembersihan event lama; jauh lebih jarang daripada sweep.
PRUNE_INTERVAL_SECONDS = 3600


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class WebhookEventDrainer:
    """Menyelesaikan event yang sudah tercatat: yang baru masuk maupun yang tertinggal."""

    def __init__(self, *, build_service: ServiceFactory, build_events: EventsFactory) -> None:
        self._build_service = build_service
        self._build_events = build_events
        self._last_prune = 0.0

    async def drain_one(self, event_id: str) -> None:
        """Jalur cepat sesudah webhook membalas 200; kalau gagal, sweeper yang melanjutkan."""
        async with session_scope() as session:
            event = await self._build_events(session).claim_one(
                event_id=event_id, max_attempts=constants.WEBHOOK_EVENT_MAX_ATTEMPTS
            )
            await session.commit()

        if event is not None:
            await self._process(event)

    async def sweep(self) -> int:
        """Ambil sebatch event tertunda dan kerjakan; kembalikan jumlah yang diproses."""
        stuck_before = utcnow() - timedelta(minutes=constants.WEBHOOK_EVENT_STUCK_MINUTES)
        async with session_scope() as session:
            events = await self._build_events(session).claim_batch(
                limit=constants.WEBHOOK_DRAIN_BATCH,
                max_attempts=constants.WEBHOOK_EVENT_MAX_ATTEMPTS,
                stuck_before=stuck_before,
            )
            await session.commit()

        for event in events:
            await self._process(event)
        return len(events)

    async def prune(self) -> int:
        processed_before = utcnow() - timedelta(days=constants.WEBHOOK_EVENT_RETENTION_DAYS)
        async with session_scope() as session:
            removed = await self._build_events(session).prune_done(
                processed_before=processed_before
            )
            await session.commit()
        return removed

    async def run_forever(self) -> None:
        """Loop sweeper; state-nya di Postgres, jadi restart tidak menghilangkan pekerjaan."""
        while True:
            try:
                handled = await self.sweep()
                if handled:
                    logger.info(f"webhook drain: {handled} event tertunda diproses")
                await self._prune_if_due()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("webhook drain: sweep gagal")

            await asyncio.sleep(constants.WEBHOOK_SWEEP_INTERVAL_SECONDS)

    async def _prune_if_due(self) -> None:
        now = asyncio.get_running_loop().time()
        if now - self._last_prune < PRUNE_INTERVAL_SECONDS:
            return
        self._last_prune = now
        removed = await self.prune()
        if removed:
            logger.info(f"webhook drain: {removed} event lama dibuang")

    async def _process(self, event: WaWebhookEvent) -> None:
        try:
            payload = WAWebhookBody.model_validate(event.payload)
        except ValidationError as e:
            logger.warning(f"webhook drain: payload {event.id} tidak dikenali ({e})")
            await self._finish(event.id, error=str(e), permanent=True)
            return

        try:
            async with session_scope() as session:
                await self._build_service(session).process(payload)
        except Exception as e:
            logger.exception(f"webhook drain: gagal memproses {event.id}")
            await self._finish(event.id, error=f"{type(e).__name__}: {e}")
            return

        await self._finish(event.id, error=None)

    async def _finish(self, event_id: str, *, error: str | None, permanent: bool = False) -> None:
        """Bookkeeping di session sendiri supaya rollback pemrosesan tidak ikut membatalkannya."""
        try:
            async with session_scope() as session:
                events = self._build_events(session)
                if error is None:
                    await events.mark_done(event_id)
                elif permanent:
                    await events.mark_failed(event_id=event_id, error=error)
                else:
                    await events.release(
                        event_id=event_id,
                        error=error,
                        max_attempts=constants.WEBHOOK_EVENT_MAX_ATTEMPTS,
                    )
                await session.commit()
        except Exception:
            # Status gagal ditulis; baris tetap processing dan diambil sweeper saat dianggap macet.
            logger.exception(f"webhook drain: gagal menandai {event_id}")
