"""Katalog provider dan model LLM yang dapat dipilih oleh agent."""

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.llm.payload import model_payload, provider_payload
from app.modules.llm.repository import LlmRepository
from app.modules.llm.schema import (
    ModelCreateRequest,
    ModelListRequest,
    ProviderCreateRequest,
    ProviderListRequest,
    ProviderUpdateRequest,
)
from app.shared import pagination
from app.shared.response import ApiError


def _required(value: str, field: str, maximum: int | None = None) -> str:
    result = value.strip()
    if not result:
        raise ApiError(400, f"{field} is required")
    if maximum is not None and len(result) > maximum:
        raise ApiError(400, f"{field} exceeds {maximum} characters")
    return result


def _description(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class LlmService:
    def __init__(self, session: AsyncSession, *, auth: AuthService, repo: LlmRepository) -> None:
        self._session = session
        self._auth = auth
        self._repo = repo

    async def providers(self, req: ProviderListRequest, token: str) -> dict[str, Any]:
        await self._auth.authenticate(token)
        page, size = pagination.normalize(req.page, req.page_size)
        total = await self._repo.count_providers()
        rows = await self._repo.list_providers(limit=size, skip=pagination.offset(page, size))
        return {
            "list": [provider_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def create_provider(self, req: ProviderCreateRequest, token: str) -> dict[str, Any]:
        await self._admin(token, resource="provider")
        try:
            provider = await self._repo.create_provider(
                api_provider=_required(req.api_provider.lower(), "api_provider", 20),
                display_name=_required(req.display_name, "display_name", 100),
                image_url=str(req.image_url) if req.image_url is not None else None,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ApiError(409, "provider already exists") from exc
        return provider_payload(provider)

    async def update_provider(self, req: ProviderUpdateRequest, token: str) -> dict[str, Any]:
        await self._admin(token, resource="provider")
        if not {"display_name", "image_url"} & req.model_fields_set:
            raise ApiError(400, "no fields to update")
        provider = await self._repo.find_provider(req.id)
        if provider is None:
            raise ApiError(404, "provider not found")
        if "display_name" in req.model_fields_set:
            provider.display_name = _required(req.display_name or "", "display_name", 100)
        if "image_url" in req.model_fields_set:
            provider.image_url = str(req.image_url) if req.image_url is not None else None
        await self._session.commit()
        await self._session.refresh(provider)
        return provider_payload(provider)

    async def models(self, req: ModelListRequest, token: str) -> dict[str, Any]:
        await self._auth.authenticate(token)
        page, size = pagination.normalize(req.page, req.page_size)
        total = await self._repo.count_models()
        rows = await self._repo.list_models(limit=size, skip=pagination.offset(page, size))
        return {
            "list": [model_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def create_model(self, req: ModelCreateRequest, token: str) -> dict[str, Any]:
        await self._admin(token)
        if await self._repo.find_provider(req.provider_id) is None:
            raise ApiError(404, "provider not found")
        try:
            model = await self._repo.create_model(
                provider_id=req.provider_id,
                api_model=_required(req.api_model, "api_model", 100),
                display_name=_required(req.display_name, "display_name", 100),
                description=_description(req.description),
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ApiError(409, "model already exists") from exc
        model = await self._repo.find_model(model.id)
        assert model is not None
        return model_payload(model)

    async def _admin(self, token: str, *, resource: str = "model") -> None:
        user = await self._auth.authenticate(token)
        if user["role"] != "Super Admin":
            raise ApiError(403, f"{resource} management denied")
