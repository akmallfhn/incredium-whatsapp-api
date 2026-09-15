from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# create_type=False: enum-nya sudah ada di Postgres, dibuat lewat DDL di docs/db.
STATUS_ENUM = ENUM("active", "inactive", name="status_enum", create_type=False)


class MetaApp(Base):
    """Satu aplikasi Meta. app_secret & verify token melekat di sini, bukan di tenant."""

    __tablename__ = "meta_apps"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    name: Mapped[str] = mapped_column(String)
    app_id: Mapped[str] = mapped_column(String)
    app_secret: Mapped[str] = mapped_column(Text)
    webhook_verify_token: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(STATUS_ENUM, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class MetaConnection(Base):
    """Satu WABA milik tenant; satu baris satu nomor WhatsApp Business."""

    __tablename__ = "meta_connections"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    meta_app_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("meta_apps.id"))
    wa_business_id: Mapped[str] = mapped_column(String)
    wa_phone_number_id: Mapped[str] = mapped_column(String)
    display_number: Mapped[str | None] = mapped_column(String)
    access_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(STATUS_ENUM, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
