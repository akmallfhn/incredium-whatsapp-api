from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.lead.repository import LeadRepository
from app.modules.lead.schema import LeadChangeModeRequest, LeadDetailsRequest, LeadUpdateRequest
from app.modules.whatsapp.entity import WaConversation, WaLead
from app.shared.response import ApiError


def _lead_payload(lead: WaLead) -> dict[str, Any]:
    return {
        "conv_id": lead.conv_id,
        "stage_id": lead.stage_id,
        "handler_id": lead.handler_id,
        "mode": lead.mode,
        "note": lead.note,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


class LeadService:
    def __init__(self, session: AsyncSession, *, auth: AuthService, leads: LeadRepository) -> None:
        self._session = session
        self._auth = auth
        self._leads = leads

    async def _conversation(self, conv_id: str, token: str) -> WaConversation:
        user = await self._auth.authenticate(token)
        if not conv_id.strip():
            raise ApiError(400, "conv_id is required")
        conversation = await self._leads.conversation(conv_id)
        if conversation is None or not any(
            tenant["id"] == conversation.tenant_id for tenant in user["tenants"]
        ):
            raise ApiError(404, "conversation not found")
        return conversation

    async def change_mode(self, req: LeadChangeModeRequest, token: str) -> dict[str, Any]:
        await self._conversation(req.conv_id, token)
        lead = await self._leads.lead(req.conv_id)
        if lead is None:
            raise ApiError(404, "lead not found")
        lead.mode = req.mode
        await self._session.commit()
        await self._session.refresh(lead)
        return _lead_payload(lead)

    async def details(self, req: LeadDetailsRequest, token: str) -> dict[str, Any]:
        await self._conversation(req.conv_id, token)
        lead = await self._leads.find(req.conv_id)
        if lead is None:
            raise ApiError(404, "lead not found")
        return _lead_payload(lead)

    async def update(self, req: LeadUpdateRequest, token: str) -> dict[str, Any]:
        conversation = await self._conversation(req.conv_id, token)
        fields = req.model_fields_set.intersection({"handler_id", "note", "stage_id"})
        if not fields:
            raise ApiError(400, "at least one field is required")
        lead = await self._leads.lead(req.conv_id)
        if lead is None:
            raise ApiError(404, "lead not found")
        if "handler_id" in fields:
            if (
                req.handler_id is not None
                and await self._leads.handler(conversation.tenant_id, str(req.handler_id)) is None
            ):
                raise ApiError(404, "handler not found")
            lead.handler_id = str(req.handler_id) if req.handler_id else None
        if "stage_id" in fields:
            if req.stage_id is not None and not req.stage_id.strip():
                raise ApiError(400, "stage_id is required")
            if (
                req.stage_id is not None
                and await self._leads.stage(conversation.tenant_id, req.stage_id) is None
            ):
                raise ApiError(404, "lead stage not found")
            lead.stage_id = req.stage_id
        if "note" in fields:
            lead.note = req.note
        await self._session.commit()
        await self._session.refresh(lead)
        return _lead_payload(lead)
