"""Pemrosesan webhook Meta dan layanan inbox percakapan serta chat WhatsApp."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.modules.auth.service import AuthService
from app.modules.meta.repository import ConnectionContext, MetaConnectionRepository
from app.modules.tenant.repository import TenantRepository
from app.modules.whatsapp.entity import (
    CHAT_STATUS_DELIVERED,
    CHAT_STATUS_FAILED,
    CHAT_STATUS_READ,
    CHAT_STATUS_SENT,
    DIRECTION_INBOUND,
    DIRECTION_OUTBOUND,
    SENDER_TYPE_ADMIN,
    SENDER_TYPE_USER,
    WaChat,
    WaConversation,
)
from app.modules.whatsapp.meta_client import MetaMediaClient, MetaMessageClient, MetaSendError
from app.modules.whatsapp.repository import (
    ConversationFilter,
    ConversationRow,
    WaChatRepository,
    WaConversationRepository,
)
from app.modules.whatsapp.schema import (
    ChatListRequest,
    ConversationAsReadRequest,
    ConversationListRequest,
    SendMessageRequest,
    WAWebhookBody,
)
from app.shared import pagination
from app.shared.pdf import shrink_pdf
from app.shared.response import ApiError
from app.shared.storage import SupabaseStorage

logger = logging.getLogger(__name__)

SUPPORTED_MESSAGE_TYPES = {"audio", "contacts", "document", "image", "sticker", "text", "video"}
# Tipe pesan yang attachment-nya beneran file (didownload dari Meta & diupload ke Storage).
MEDIA_MESSAGE_TYPES = {"audio", "document", "image", "sticker", "video"}
PDF_MIME = "application/pdf"

# Di luar jendela ini Meta hanya menerima pesan template.
CUSTOMER_SERVICE_WINDOW = timedelta(hours=24)
MAX_TEXT_LENGTH = 4096

HANDLED_FIELDS = ("messages", "smb_message_echoes")
# Field yang tidak membawa pesan tapi mengabarkan akun/koneksi berubah; dicatat lebih keras.
CRITICAL_FIELDS = ("account_update", "security", "phone_number_quality_update")


def _can_access_tenant(user: dict[str, Any], tenant_id: str) -> bool:
    return any(tenant["id"] == tenant_id for tenant in user["tenants"])


@dataclass(frozen=True)
class ProcessOutcome:
    """Hasil satu event: berapa change yang dikerjakan dan field apa saja yang dilewati."""

    handled: int
    skipped: tuple[str, ...]


_STATUS_MAP = {
    "sent": CHAT_STATUS_SENT,
    "delivered": CHAT_STATUS_DELIVERED,
    "read": CHAT_STATUS_READ,
    "played": CHAT_STATUS_READ,
    "failed": CHAT_STATUS_FAILED,
}
_STATUS_TIMESTAMP_FIELD = {
    CHAT_STATUS_SENT: "sent_at",
    CHAT_STATUS_DELIVERED: "delivered_at",
    CHAT_STATUS_READ: "read_at",
    CHAT_STATUS_FAILED: "failed_at",
}


def unix_to_datetime(value: Any) -> datetime:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        ts = 0
    return datetime.fromtimestamp(ts, tz=timezone.utc)


class WhatsAppWebhookService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        connections: MetaConnectionRepository,
        conversations: WaConversationRepository,
        chats: WaChatRepository,
        media: MetaMediaClient,
        storage: SupabaseStorage,
    ) -> None:
        self._session = session
        self._connections = connections
        self._conversations = conversations
        self._chats = chats
        self._media = media
        self._storage = storage

    async def process(self, payload: WAWebhookBody) -> ProcessOutcome:
        """Kerjakan satu payload; pemanggil memakai hasilnya untuk menandai statusnya."""
        handled = 0
        skipped: list[str] = []

        for entry in payload.entry:
            for change in entry.changes:
                if change.field not in HANDLED_FIELDS:
                    skipped.append(change.field)
                    if change.field in CRITICAL_FIELDS:
                        # Inilah yang mengabarkan link coexistence putus atau nomor dilepas.
                        logger.error(
                            f"wa-meta webhook: field {change.field} diterima tapi belum ditangani; "
                            f"payload tersimpan di wa_webhook_events"
                        )
                    else:
                        logger.warning(f"wa-meta webhook: field {change.field} dilewati")
                    continue

                value = change.value
                phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
                if not phone_number_id:
                    continue

                try:
                    ctx = await self._connections.find_context_by_phone_number_id(phone_number_id)
                except Exception:
                    await self._session.rollback()
                    logger.exception(
                        f"wa-meta webhook: connection lookup failed for {phone_number_id}"
                    )
                    continue

                if ctx is None:
                    logger.info(
                        f"wa-meta webhook: no active connection for "
                        f"phone_number_id={phone_number_id}"
                    )
                    continue

                if change.field == "smb_message_echoes":
                    await self._handle_echoes(ctx, value)
                else:
                    await self._handle_messages(ctx, value)

                await self._handle_statuses(ctx, value)
                handled += 1

        return ProcessOutcome(handled=handled, skipped=tuple(skipped))

    # --- Pesan masuk dari pelanggan ----------------------------------------------
    async def _handle_messages(self, ctx: ConnectionContext, value: dict[str, Any]) -> None:
        messages = value.get("messages") or []
        if not messages:
            return

        contacts = value.get("contacts") or []
        full_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

        for msg in messages:
            msg_type = msg.get("type")
            if msg_type not in SUPPORTED_MESSAGE_TYPES:
                continue

            is_text = msg_type == "text"
            attachment = await self._resolve_attachment(ctx, msg_type, msg)

            wam_id = msg.get("id", "")
            try:
                await self._append_inbound_chat(
                    tenant_id=ctx.tenant_id,
                    full_name=full_name,
                    phone_number=msg.get("from", ""),
                    wam_id=wam_id,
                    msg_type=msg_type,
                    message=msg.get("text", {}).get("body", "") if is_text else "",
                    attachment=attachment,
                    sent_at_unix=msg.get("timestamp"),
                    context_wam_id=(msg.get("context") or {}).get("id"),
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                logger.exception(f"wa-meta webhook: failed to store wam_id={wam_id}")

    async def _append_inbound_chat(
        self,
        *,
        tenant_id: str,
        full_name: str,
        phone_number: str,
        wam_id: str,
        msg_type: str,
        message: str,
        attachment: Any | None,
        sent_at_unix: Any,
        context_wam_id: str | None,
    ) -> None:
        conv = await self._conversations.find_or_create(
            tenant_id=tenant_id, full_name=full_name, phone_number=phone_number
        )

        reply_to_id = None
        if context_wam_id:
            replied_to = await self._chats.find_by_wam_id(context_wam_id, conv_id=conv.id)
            reply_to_id = replied_to.id if replied_to else None

        await self._chats.upsert_message(
            conv_id=conv.id,
            wam_id=wam_id,
            direction=DIRECTION_INBOUND,
            sender_type=SENDER_TYPE_USER,
            msg_type=msg_type,
            message=message,
            attachment=attachment,
            reply_to_id=reply_to_id,
            created_at=unix_to_datetime(sent_at_unix),
        )

    # --- Echo pesan yang dikirim staff dari WhatsApp Business App (coexistence) ---
    async def _handle_echoes(self, ctx: ConnectionContext, value: dict[str, Any]) -> None:
        for echo in value.get("message_echoes") or []:
            msg_type = echo.get("type")
            if msg_type not in SUPPORTED_MESSAGE_TYPES:
                continue

            is_text = msg_type == "text"
            wam_id = echo.get("id", "")
            sent_at = unix_to_datetime(echo.get("timestamp"))
            attachment = await self._resolve_attachment(ctx, msg_type, echo)
            try:
                conv = await self._conversations.find_or_create(
                    tenant_id=ctx.tenant_id, full_name="", phone_number=echo.get("to", "")
                )
                # Meta tidak pernah mengirim status sent untuk pesan dari app; echo itulah buktinya.
                await self._chats.upsert_message(
                    conv_id=conv.id,
                    wam_id=wam_id,
                    direction=DIRECTION_OUTBOUND,
                    sender_type=SENDER_TYPE_ADMIN,
                    msg_type=msg_type,
                    message=echo.get("text", {}).get("body", "") if is_text else "",
                    attachment=attachment,
                    created_at=sent_at,
                    sent_at=sent_at,
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                logger.exception(f"wa-meta webhook: failed to store echo {wam_id}")

    # --- Status delivery pesan keluar ---------------------------------------------
    async def _handle_statuses(self, ctx: ConnectionContext, value: dict[str, Any]) -> None:
        for status in value.get("statuses") or []:
            wam_id = status.get("id", "")
            try:
                await self._update_status(
                    tenant_id=ctx.tenant_id,
                    phone_number=status.get("recipient_id", ""),
                    wam_id=wam_id,
                    status=status.get("status", ""),
                    updated_at_unix=status.get("timestamp"),
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                logger.exception(f"wa-meta webhook: failed to update status {wam_id}")

    async def _update_status(
        self,
        *,
        tenant_id: str,
        phone_number: str,
        wam_id: str,
        status: str,
        updated_at_unix: Any,
    ) -> None:
        mapped = _STATUS_MAP.get(status)
        if not mapped:
            return

        updated_at = unix_to_datetime(updated_at_unix)
        timestamp_field = _STATUS_TIMESTAMP_FIELD[mapped]

        chat = await self._chats.find_by_wam_id(wam_id)
        if chat is not None:
            chat.status = mapped
            setattr(chat, timestamp_field, updated_at)
            return

        # Pesan keluar lewat WhatsApp Business App (coexistence) yang belum pernah tercatat.
        conv = await self._conversations.find_or_create(
            tenant_id=tenant_id, full_name="", phone_number=phone_number
        )
        # Upsert, bukan insert: echo pesan ini bisa menyusul dan harus mengisi baris yang sama.
        await self._chats.upsert_status(
            conv_id=conv.id,
            wam_id=wam_id,
            status=mapped,
            timestamp_field=timestamp_field,
            occurred_at=updated_at,
        )

    # --- Attachment: download dari Meta, simpan ke Supabase Storage ----------------
    async def _resolve_attachment(
        self, ctx: ConnectionContext, msg_type: str, payload: dict[str, Any]
    ) -> Any | None:
        """Attachment siap simpan: yang berupa file ditarik ke Storage, sisanya apa adanya."""
        if msg_type == "text":
            return None

        attachment = payload.get(msg_type)
        if attachment is None or msg_type not in MEDIA_MESSAGE_TYPES:
            return attachment

        return await self._save_media_attachment(
            ctx=ctx, media_type=msg_type, attachment=attachment
        )

    async def _save_media_attachment(
        self,
        *,
        ctx: ConnectionContext,
        media_type: str,
        attachment: dict[str, Any],
    ) -> dict[str, Any]:
        """Sisipkan `storage_url` ke attachment. Media gagal disimpan tidak membatalkan pesannya."""
        media_id = attachment.get("id")
        if not ctx.access_token or not media_id or not self._storage.enabled:
            return attachment

        existing_url = await self._find_existing_media(ctx, attachment.get("sha256"))
        if existing_url:
            return {**attachment, "storage_url": existing_url}

        try:
            content, mime_type = await self._media.fetch(
                access_token=ctx.access_token,
                phone_number_id=ctx.phone_number_id,
                media_id=media_id,
            )
            if mime_type == PDF_MIME:
                content = await self._shrink_pdf(content, media_id)
            object_path = self._storage.object_path(
                ctx.tenant_slug, media_type, media_id, mime_type
            )
            storage_url = await self._storage.upload(object_path, content, mime_type)
            return {**attachment, "storage_url": storage_url}
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500]
            logger.exception(f"wa-meta webhook: failed to save media {media_id} ({body})")
            return attachment
        except Exception:
            logger.exception(f"wa-meta webhook: failed to save media {media_id}")
            return attachment

    async def _find_existing_media(self, ctx: ConnectionContext, sha256: Any) -> str | None:
        """File yang sama pernah disimpan tenant ini; gagal lookup cukup berarti upload ulang."""
        if not sha256:
            return None
        try:
            return await self._chats.find_storage_url_by_sha256(
                tenant_id=ctx.tenant_id, sha256=str(sha256)
            )
        except Exception:
            await self._session.rollback()
            logger.exception(f"wa-meta webhook: lookup sha256 {sha256} gagal")
            return None

    async def _shrink_pdf(self, content: bytes, media_id: str) -> bytes:
        """Di thread terpisah: pikepdf/Pillow CPU-bound dan akan menahan event loop webhook."""
        shrunk = await asyncio.to_thread(shrink_pdf, content, constants.SUPABASE_MAX_OBJECT_BYTES)
        if len(shrunk) < len(content):
            logger.info(
                f"wa-meta webhook: pdf {media_id} diperkecil {len(content)} -> {len(shrunk)} bytes"
            )
        return shrunk


class WhatsAppInboxService:
    """Layanan inbox dashboard: baca percakapan dan chat, tandai dibaca, kirim balasan."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        auth: AuthService,
        tenants: TenantRepository,
        connections: MetaConnectionRepository,
        conversations: WaConversationRepository,
        chats: WaChatRepository,
        messages: MetaMessageClient,
    ) -> None:
        self._session = session
        self._auth = auth
        self._tenants = tenants
        self._connections = connections
        self._conversations = conversations
        self._chats = chats
        self._messages = messages

    async def conversations(self, req: ConversationListRequest, token: str) -> dict[str, Any]:
        user = await self._auth.authenticate(token)
        if not req.tenant_id.strip():
            raise ApiError(400, "tenant_id is required")
        if not _can_access_tenant(user, req.tenant_id):
            raise ApiError(403, "tenant access denied")
        if await self._tenants.find_by_id(req.tenant_id) is None:
            raise ApiError(404, "tenant not found")

        f = ConversationFilter(
            tenant_id=req.tenant_id,
            search=(req.search or "").strip() or None,
            stage_id=(req.stage_id or "").strip() or None,
            mode=req.mode,
            by_handler="handler_id" in req.model_fields_set,
            handler_id=str(req.handler_id) if req.handler_id else None,
        )
        page, page_size = pagination.normalize(req.page, req.page_size)
        total = await self._conversations.count_filtered(f)
        rows = await self._conversations.list_filtered(
            f, limit=page_size, skip=pagination.offset(page, page_size)
        )
        now = datetime.now(timezone.utc)
        return {
            "list": [_conversation_payload(row, now) for row in rows],
            "metapaging": pagination.meta(total, page, page_size),
        }

    async def chats(self, req: ChatListRequest, token: str) -> dict[str, Any]:
        conv = await self._accessible_conversation(req.conv_id, token)

        page, page_size = pagination.normalize(req.page, req.page_size)
        total = await self._chats.count_by_conversation(conv.id)
        rows = await self._chats.list_by_conversation(
            conv_id=conv.id, limit=page_size, skip=pagination.offset(page, page_size)
        )
        return {
            "list": [_chat_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, page_size),
        }

    async def mark_as_read(self, req: ConversationAsReadRequest, token: str) -> dict[str, Any]:
        conv = await self._accessible_conversation(req.conv_id, token)
        last_read_id = await self._conversations.mark_as_read(conv.id)
        await self._session.commit()
        return {"id": conv.id, "last_read_id": last_read_id, "unread_count": 0}

    async def send(self, req: SendMessageRequest, token: str) -> dict[str, Any]:
        conv = await self._accessible_conversation(req.conv_id, token)
        body = req.message.strip()
        if not body:
            raise ApiError(400, "message is required")
        if len(body) > MAX_TEXT_LENGTH:
            raise ApiError(400, f"message exceeds {MAX_TEXT_LENGTH} characters")

        reply_to_wam_id = None
        if req.reply_to_id:
            reply_to = await self._chats.find_in_conversation(
                chat_id=req.reply_to_id, conv_id=conv.id
            )
            if reply_to is None:
                raise ApiError(404, "reply message not found")
            reply_to_wam_id = reply_to.wam_id

        # Di luar jendela 24 jam Meta tetap membalas 200 lalu menggagalkan pesannya lewat webhook.
        last_inbound_at = await self._chats.last_inbound_at(conv.id)
        if _window_expired(last_inbound_at, datetime.now(timezone.utc)):
            raise ApiError(409, "customer service window has expired")

        ctx = await self._connections.find_context_by_tenant_id(conv.tenant_id)
        if ctx is None or not ctx.access_token:
            raise ApiError(409, "tenant has no active whatsapp connection")

        try:
            wam_id = await self._messages.send_text(
                access_token=ctx.access_token,
                phone_number_id=ctx.phone_number_id,
                to=conv.phone_number,
                body=body,
                reply_to_wam_id=reply_to_wam_id,
            )
        except MetaSendError as exc:
            logger.warning(f"wa-meta send: gagal kirim ke conv={conv.id}: {exc}")
            raise ApiError(500, f"failed to send message: {exc}") from exc

        # Upsert karena webhook status dari Meta bisa lebih dulu membuat baris penampungnya.
        await self._chats.upsert_message(
            conv_id=conv.id,
            wam_id=wam_id,
            direction=DIRECTION_OUTBOUND,
            sender_type=SENDER_TYPE_ADMIN,
            msg_type="text",
            message=body,
            reply_to_id=req.reply_to_id,
        )
        await self._session.commit()

        chat = await self._chats.find_by_wam_id(wam_id)
        if chat is None:
            raise ApiError(500, "an unexpected error occurred")
        return _chat_payload(chat)

    async def _accessible_conversation(self, conv_id: str, token: str) -> WaConversation:
        """Percakapan di luar akses tenant pengguna dijawab 404, bukan 403, supaya tidak bocor."""
        user = await self._auth.authenticate(token)
        if not conv_id.strip():
            raise ApiError(400, "conv_id is required")
        conv = await self._conversations.find_by_id(conv_id)
        if conv is None or not _can_access_tenant(user, conv.tenant_id):
            raise ApiError(404, "conversation not found")
        return conv


def _window_expired(last_inbound_at: datetime | None, now: datetime) -> bool:
    return last_inbound_at is None or now - last_inbound_at >= CUSTOMER_SERVICE_WINDOW


def _conversation_payload(row: ConversationRow, now: datetime) -> dict[str, Any]:
    conv, last = row.conversation, row.last_chat
    return {
        "id": conv.id,
        "tenant_id": conv.tenant_id,
        "full_name": conv.full_name,
        "phone_number": conv.phone_number,
        "last_read_id": conv.last_read_id,
        "unread_count": row.unread_count,
        "window_expired": _window_expired(row.last_inbound_at, now),
        "last_message": last.message if last else None,
        "last_message_type": last.type if last else None,
        "last_message_direction": last.direction if last else None,
        "last_message_status": last.status if last else None,
        "last_message_at": last.created_at.isoformat() if last else None,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


def _chat_payload(row: WaChat) -> dict[str, Any]:
    return {
        "id": row.id,
        "conv_id": row.conv_id,
        "wam_id": row.wam_id,
        "direction": row.direction,
        "sender_type": row.sender_type,
        "reply_to_id": row.reply_to_id,
        "type": row.type,
        "message": row.message,
        "attachment": row.attachment,
        "status": row.status,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "delivered_at": row.delivered_at.isoformat() if row.delivered_at else None,
        "read_at": row.read_at.isoformat() if row.read_at else None,
        "failed_at": row.failed_at.isoformat() if row.failed_at else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
