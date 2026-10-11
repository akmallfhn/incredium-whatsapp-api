from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class WAWebhookChange(BaseModel):
    field: str
    value: dict[str, Any] = Field(default_factory=dict)


class WAWebhookEntry(BaseModel):
    id: str
    changes: list[WAWebhookChange] = Field(default_factory=list)


class WAWebhookBody(BaseModel):
    object: str
    entry: list[WAWebhookEntry] = Field(default_factory=list)


class ConversationListRequest(BaseModel):
    tenant_id: str
    search: str | None = None
    stage_id: str | None = None
    mode: Literal["ai", "human"] | None = None
    # null eksplisit berarti "belum ada handler"; field tidak dikirim berarti tanpa filter.
    handler_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class ConversationAsReadRequest(BaseModel):
    conv_id: str


class SendMessageRequest(BaseModel):
    conv_id: str
    message: str
    reply_to_id: str | None = None


class ChatListRequest(BaseModel):
    conv_id: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
