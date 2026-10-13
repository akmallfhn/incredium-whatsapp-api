from datetime import datetime

from sqlalchemy import CHAR, BigInteger, ForeignKey, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.tenant.entity import STATUS_ENUM


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("llm_models.id"))
    name: Mapped[str] = mapped_column(String(100))
    system_prompt: Mapped[str] = mapped_column(Text)
    transfer_conditions: Mapped[str] = mapped_column(Text, server_default=text("''"))
    config_version: Mapped[int] = mapped_column(BigInteger, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class AgentKnowledgeSource(Base):
    __tablename__ = "agent_knowledge_sources"

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    agent_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("agents.id"))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    source_uri: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(STATUS_ENUM, server_default=text("'inactive'"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )


class AgentReplyJob(Base):
    __tablename__ = "agent_reply_jobs"

    conv_id: Mapped[str] = mapped_column(
        CHAR(21), ForeignKey("wa_conversations.id"), primary_key=True
    )
    latest_inbound_chat_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("wa_chats.id"))
    wa_phone_number_id: Mapped[str] = mapped_column(String)
    generation: Mapped[int] = mapped_column(BigInteger, server_default=text("1"))
    claimed_generation: Mapped[int | None] = mapped_column(BigInteger)
    due_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    claimed_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")
    )
