from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LeadChangeModeRequest(BaseModel):
    conv_id: str
    mode: Literal["ai", "human"]


class LeadDetailsRequest(BaseModel):
    conv_id: str


class LeadStageListRequest(BaseModel):
    tenant_id: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class LeadUpdateRequest(BaseModel):
    conv_id: str
    handler_id: UUID | None = None
    note: str | None = None
    stage_id: str | None = None
