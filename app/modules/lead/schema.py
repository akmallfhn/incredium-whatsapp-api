from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class LeadChangeModeRequest(BaseModel):
    conv_id: str
    mode: Literal["ai", "human"]


class LeadUpdateRequest(BaseModel):
    conv_id: str
    handler_id: UUID | None = None
    note: str | None = None
    stage_id: str | None = None
