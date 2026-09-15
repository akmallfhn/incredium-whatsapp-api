import logging
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_scope
from app.modules.agents.lead_evaluation.service import LeadEvaluationService
from app.modules.meta.repository import MetaAppRepository
from app.modules.whatsapp.schema import WAWebhookBody
from app.modules.whatsapp.service import WhatsAppWebhookService
from app.shared.security import verify_meta_signature, verify_meta_token

logger = logging.getLogger(__name__)

ServiceFactory = Callable[[AsyncSession], WhatsAppWebhookService]
EvaluatorFactory = Callable[[AsyncSession], LeadEvaluationService]


@dataclass(frozen=True)
class AppCredentials:
    app_secret: str
    verify_token: str


async def resolve_app_credentials(app_id: str) -> AppCredentials | None:
    """Kredensial App pemanggil; sumbernya cuma meta_apps, App tak dikenal dapat None."""
    try:
        async with session_scope() as session:
            app = await MetaAppRepository(session).find_by_app_id(app_id)
    except Exception:
        logger.exception("wa-meta webhook: meta_apps lookup failed")
        return None

    if app is None:
        return None
    return AppCredentials(app.app_secret, app.webhook_verify_token)


def register_whatsapp_routes(
    rg: APIRouter, build_service: ServiceFactory, build_evaluator: EvaluatorFactory
) -> None:
    router = APIRouter(prefix="/webhook/whatsapp", tags=["webhook:whatsapp-meta"])

    async def process(payload: WAWebhookBody) -> None:
        # Session sendiri: session milik request sudah ditutup waktu background task jalan.
        async with session_scope() as session:
            conv_ids = await build_service(session).process(payload)

        # Evaluasi di session terpisah supaya panggilan LLM tidak menahan koneksi tulis.
        for conv_id in conv_ids:
            try:
                async with session_scope() as session:
                    await build_evaluator(session).evaluate(conv_id)
            except Exception:
                logger.exception(f"lead-eval: unhandled failure for {conv_id}")

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
        raise HTTPException(status_code=403, detail="Forbidden")

    @router.post("/callback/{app_id}")
    async def receive_callback(
        app_id: str, request: Request, background_tasks: BackgroundTasks
    ) -> Response:
        raw_body = await request.body()

        creds = await resolve_app_credentials(app_id)
        if creds is None:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Signature dicek sebelum body diparse: isi payload belum boleh dipercaya sampai sini.
        if creds.app_secret:
            signature = request.headers.get("x-hub-signature-256", "")
            if not verify_meta_signature(raw_body, signature, creds.app_secret):
                raise HTTPException(status_code=401, detail="Invalid signature")

        payload = WAWebhookBody.model_validate_json(raw_body)
        if payload.object != "whatsapp_business_account":
            return Response(status_code=200)

        # Meta mengulang kirim kalau tidak dibalas cepat, jadi persist-nya di background.
        background_tasks.add_task(process, payload)
        return Response(status_code=200)

    rg.include_router(router)
