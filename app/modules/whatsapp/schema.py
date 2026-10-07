from typing import Any

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
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class ChatListRequest(BaseModel):
    conv_id: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
