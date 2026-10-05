from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, BigInteger, Boolean, ForeignKey, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSON, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.tenant.entity import STATUS_ENUM

DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"

SENDER_TYPE_USER = "user"
SENDER_TYPE_ADMIN = "admin"

MODE_AI = "ai"
MODE_HUMAN = "human"

CHAT_TYPES = (
    "audio",
    "button",
    "contacts",
    "document",
    "edit",
    "image",
    "interactive",
    "location",
    "order",
    "reaction",
    "revoke",
    "sticker",
    "system",
    "text",
    "unsupported",
    "video",
    "template",
)

EVENT_STATUS_PENDING = "pending"
EVENT_STATUS_PROCESSING = "processing"
EVENT_STATUS_DONE = "done"
EVENT_STATUS_IGNORED = "ignored"
EVENT_STATUS_FAILED = "failed"

CHAT_STATUS_SENT = "sent"
CHAT_STATUS_DELIVERED = "delivered"
CHAT_STATUS_READ = "read"
CHAT_STATUS_FAILED = "failed"

# create_type=False: enum-nya sudah ada di Postgres, dibuat lewat DDL di docs/db.
MODE_ENUM = ENUM(MODE_AI, MODE_HUMAN, name="wa_mode_enum", create_type=False)
DIRECTION_ENUM = ENUM(
    DIRECTION_INBOUND, DIRECTION_OUTBOUND, name="wac_direction_enum", create_type=False
)
SENDER_TYPE_ENUM = ENUM(
    SENDER_TYPE_USER, SENDER_TYPE_ADMIN, name="wac_sender_type_enum", create_type=False
)
CHAT_TYPE_ENUM = ENUM(*CHAT_TYPES, name="wac_type_enum", create_type=False)
WEBHOOK_EVENT_STATUS_ENUM = ENUM(
    EVENT_STATUS_PENDING,
    EVENT_STATUS_PROCESSING,
    EVENT_STATUS_DONE,
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_FAILED,
    name="wwe_status_enum",
    create_type=False,
)
CHAT_STATUS_ENUM = ENUM(
    CHAT_STATUS_SENT,
    CHAT_STATUS_DELIVERED,
    CHAT_STATUS_READ,
    CHAT_STATUS_FAILED,
    name="wac_status_enum",
    create_type=False,
)


class WaConversation(Base):
    """Satu thread WhatsApp antara tenant dan satu nomor pelanggan; hanya fakta dari webhook."""

    __tablename__ = "wa_conversations"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    full_name: Mapped[str] = mapped_column(String)
    phone_number: Mapped[str] = mapped_column(String)
    last_read_id: Mapped[str | None] = mapped_column(CHAR(21))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class WaLeadStage(Base):
    """Satu tahap lead milik tenant; urutan funnel ditentukan position."""

    __tablename__ = "wa_lead_stages"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    key: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    # Kriteria tahap ini dalam bahasa manusia; jadi bahan prompt agent penilai lead.
    description: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(STATUS_ENUM, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class WaLead(Base):
    """Data lead satu percakapan, diatur manusia atau LLM; relasi 1-1 dengan wa_conversations."""

    __tablename__ = "wa_leads"

    conv_id: Mapped[str] = mapped_column(
        CHAR(21), ForeignKey("wa_conversations.id", ondelete="CASCADE"), primary_key=True
    )
    stage_id: Mapped[str | None] = mapped_column(CHAR(21), ForeignKey("wa_lead_stages.id"))
    handler_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    mode: Mapped[str] = mapped_column(MODE_ENUM, server_default=text("'human'"))
    # Kontak tim sendiri; percakapannya dibuang dari semua query stat.
    is_internal: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    brand_name: Mapped[str | None] = mapped_column(String)
    project_value: Mapped[int | None] = mapped_column(BigInteger)
    winning_rate: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    note: Mapped[str | None] = mapped_column(String)
    # Chat terakhir yang sudah dinilai LLM; sama dengan chat terakhir berarti tidak perlu dinilai.
    evaluated_last_chat_id: Mapped[str | None] = mapped_column(CHAR(21), ForeignKey("wa_chats.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class WaChat(Base):
    """Satu pesan WhatsApp, arah masuk maupun keluar."""

    __tablename__ = "wa_chats"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    conv_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("wa_conversations.id"))
    wam_id: Mapped[str] = mapped_column(String)
    direction: Mapped[str] = mapped_column(DIRECTION_ENUM)
    sender_type: Mapped[str] = mapped_column(SENDER_TYPE_ENUM)
    reply_to_id: Mapped[str | None] = mapped_column(CHAR(21), ForeignKey("wa_chats.id"))
    type: Mapped[str] = mapped_column(CHAT_TYPE_ENUM)
    message: Mapped[str] = mapped_column(String)
    attachment: Mapped[Any | None] = mapped_column(JSON(none_as_null=True))
    status: Mapped[str | None] = mapped_column(CHAT_STATUS_ENUM)
    sent_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    read_at: Mapped[datetime | None]
    failed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class WaWebhookEvent(Base):
    """Satu event webhook Meta apa adanya; ditulis sebelum 200 dibalas supaya tidak bisa hilang."""

    __tablename__ = "wa_webhook_events"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    app_id: Mapped[str] = mapped_column(String)
    payload: Mapped[Any] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(WEBHOOK_EVENT_STATUS_ENUM, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    claimed_at: Mapped[datetime | None]
    processed_at: Mapped[datetime | None]
