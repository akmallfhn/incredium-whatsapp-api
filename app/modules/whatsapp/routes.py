import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_scope
from app.modules.meta.repository import MetaAppRepository
from app.modules.whatsapp.drain import WebhookEventDrainer
from app.modules.whatsapp.repository import WaWebhookEventRepository
from app.shared.security import verify_meta_signature, verify_meta_token

logger = logging.getLogger(__name__)

EventsFactory = Callable[[AsyncSession], WaWebhookEventRepository]

WA_OBJECT = "whatsapp_business_account"


@dataclass(frozen=True)
class AppCredentials:
    app_secret: str
    verify_token: str


async def resolve_app_credentials(app_id: str) -> AppCredentials | None:
    """Kredensial App pemanggil; None berarti App tak dikenal, bukan gagal memeriksa."""
    # Error database dibiarkan naik jadi 500; 403 berarti "ditolak", bukan "belum diperiksa".
    async with session_scope() as session:
        app = await MetaAppRepository(session).find_by_app_id(app_id)

    if app is None:
        return None
    return AppCredentials(app.app_secret, app.webhook_verify_token)


def register_whatsapp_routes(
    rg: APIRouter, build_events: EventsFactory, drainer: WebhookEventDrainer
) -> None:
    router = APIRouter(prefix="/webhook/whatsapp", tags=["webhook:whatsapp-meta"])

    # Segmen app_id wajib: tanpa itu app_secret pemanggil tak bisa ditentukan.

    @router.get("/callback/{app_id}")
    async def verify_webhook(
        app_id: str,
        hub_mode: str = Query(default="", alias="hub.mode"),
        hub_verify_token: str = Query(default="", alias="hub.verify_token"),
        hub_challenge: str = Query(default="", alias="hub.challenge"),
    ) -> PlainTextResponse:
        creds = await resolve_app_credentials(app_id)
        if (
            hub_mode == "subscribe"
            and creds is not None
            and creds.verify_token
            and verify_meta_token(hub_verify_token, creds.verify_token)
        ):
            return PlainTextResponse(hub_challenge)

        logger.warning(f"wa-meta webhook: verifikasi ditolak untuk app_id={app_id}")
        raise HTTPException(status_code=403, detail="Forbidden")

    @router.post("/callback/{app_id}")
    async def receive_callback(
        app_id: str, request: Request, background_tasks: BackgroundTasks
    ) -> Response:
        raw_body = await request.body()

        creds = await resolve_app_credentials(app_id)
        if creds is None:
            # Sistemik kalau terpicu: baris meta_apps hilang atau inactive, semua event ikut gagal.
            logger.warning(f"wa-meta webhook: app_id={app_id} tidak ada di meta_apps aktif")
            raise HTTPException(status_code=403, detail="Forbidden")

        # Signature dicek sebelum body diparse: isi payload belum boleh dipercaya sampai sini.
        if creds.app_secret:
            signature = request.headers.get("x-hub-signature-256", "")
            if not verify_meta_signature(raw_body, signature, creds.app_secret):
                # Biasanya app_secret dirotasi di Meta tapi belum diperbarui di meta_apps.
                logger.warning(f"wa-meta webhook: signature tidak cocok untuk app_id={app_id}")
                raise HTTPException(status_code=401, detail="Invalid signature")

        try:
            payload = json.loads(raw_body)
        except ValueError:
            # Tidak ada yang bisa disimpan dan mengulang tak akan menolong, jadi tetap 200.
            logger.warning(f"wa-meta webhook: body bukan JSON dari app_id={app_id}")
            return Response(status_code=200)

        if not isinstance(payload, dict) or payload.get("object") != WA_OBJECT:
            return Response(status_code=200)

        # Catat dulu, balas 200 sesudahnya: sejak baris ini commit, event tidak bisa hilang lagi.
        async with session_scope() as session:
            event_id = await build_events(session).record(app_id=app_id, payload=payload)
            await session.commit()

        # Pemrosesan tetap di luar jalur balasan; kalau mati di tengah, sweeper melanjutkannya.
        background_tasks.add_task(drainer.drain_one, event_id)
        return Response(status_code=200)

    rg.include_router(router)
