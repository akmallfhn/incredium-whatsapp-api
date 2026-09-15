from datetime import datetime

from sqlalchemy import CHAR, Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.tenant.entity import STATUS_ENUM

ROLE_SUPER_ADMIN = "Super Admin"
ROLE_ADMINISTRATOR = "Administrator"
ROLE_MEMBER = "Member"

# create_type=False: enum-nya sudah ada di Postgres, dibuat lewat DDL di docs/db.
ROLE_ENUM = ENUM(
    ROLE_SUPER_ADMIN, ROLE_ADMINISTRATOR, ROLE_MEMBER, name="user_role_enum", create_type=False
)


class User(Base):
    """Akun dashboard. Peran menentukan kewenangan, users_access menentukan tenant-nya."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    avatar: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(ROLE_ENUM, server_default=text("'Member'"))
    password_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(STATUS_ENUM, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class Token(Base):
    """Sesi login yang masih hidup. Logout menghapus barisnya, jadi JWT-nya ikut mati."""

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("TRUE"))
    token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class UserAccess(Base):
    """Tenant mana saja yang boleh diakses seorang user."""

    __tablename__ = "users_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
