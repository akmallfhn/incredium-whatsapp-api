from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.whatsapp.repository import WaWebhookEventRepository

EventsFactory = Callable[[AsyncSession], WaWebhookEventRepository]


def register_health_routes(rg: APIRouter, build_events: EventsFactory) -> None:
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @router.get("/health/db")
    async def health_db(session: AsyncSession = Depends(get_session)) -> dict:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}

    @router.get("/health/webhook")
    async def health_webhook(session: AsyncSession = Depends(get_session)) -> dict:
        """Kapan event terakhir masuk dan berapa yang belum selesai; dasar alarm webhook mati."""
        last_event_at, backlog = await build_events(session).backlog()
        idle = None
        if last_event_at is not None:
            idle = int((datetime.now(tz=timezone.utc) - last_event_at).total_seconds())
        return {
            "status": "ok",
            "last_event_at": last_event_at.isoformat() if last_event_at else None,
            "seconds_since_last_event": idle,
            "backlog": backlog,
        }

    rg.include_router(router)
