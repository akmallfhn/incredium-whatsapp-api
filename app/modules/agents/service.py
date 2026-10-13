"""CRUD konfigurasi agent dan sumber pengetahuan per tenant."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.entity import Agent, AgentKnowledgeSource
from app.modules.agents.repository import AgentRepository
from app.modules.agents.schema import (
    AgentCreateRequest,
    AgentDeleteRequest,
    AgentDetailsRequest,
    AgentListRequest,
    AgentSelectRequest,
    AgentUpdateRequest,
    KnowledgeCreateRequest,
    KnowledgeDeleteRequest,
    KnowledgeDetailsRequest,
    KnowledgeListRequest,
    KnowledgeUpdateRequest,
)
from app.modules.auth.service import AuthService
from app.modules.llm.entity import LlmModel
from app.modules.llm.payload import model_payload
from app.modules.llm.repository import LlmRepository
from app.shared import pagination
from app.shared.agent_cache import AgentCache
from app.shared.response import ApiError

WRITE_ROLES = {"Super Admin", "Administrator"}


def _required(value: str, field: str, maximum: int | None = None) -> str:
    result = value.strip()
    if not result:
        raise ApiError(400, f"{field} is required")
    if maximum is not None and len(result) > maximum:
        raise ApiError(400, f"{field} exceeds {maximum} characters")
    return result


def _agent_payload(agent: Agent, model: LlmModel | None, active_id: str | None) -> dict[str, Any]:
    model_data = model_payload(model) if model is not None else None
    if model_data is not None:
        model_data.pop("description")
    return {
        "id": agent.id,
        "tenant_id": agent.tenant_id,
        "model_id": agent.model_id,
        "model": model_data,
        "name": agent.name,
        "personality": agent.personality,
        "system_prompt": agent.system_prompt,
        "transfer_conditions": agent.transfer_conditions,
        "config_version": agent.config_version,
        "is_active": agent.id == active_id,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


def _source_payload(source: AgentKnowledgeSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "agent_id": source.agent_id,
        "title": source.title,
        "kind": source.kind,
        "source_uri": source.source_uri,
        "content": source.content,
        "status": source.status,
        "created_at": source.created_at.isoformat(),
        "updated_at": source.updated_at.isoformat(),
    }


class AgentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        auth: AuthService,
        repo: AgentRepository,
        models: LlmRepository,
        cache: AgentCache,
    ) -> None:
        self._session = session
        self._auth = auth
        self._repo = repo
        self._models = models
        self._cache = cache

    async def _access(self, token: str, tenant_id: str, *, write: bool = False) -> None:
        tenant_id = _required(tenant_id, "tenant_id")
        user = await self._auth.authenticate(token)
        if not any(item["id"] == tenant_id for item in user["tenants"]):
            raise ApiError(403, "tenant access denied")
        if write and user["role"] not in WRITE_ROLES:
            raise ApiError(403, "agent management denied")

    async def list_agents(self, req: AgentListRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id)
        tenant = await self._repo.tenant(req.tenant_id)
        if tenant is None:
            raise ApiError(404, "tenant not found")
        page, size = pagination.normalize(req.page, req.page_size)
        total = await self._repo.count_agents(req.tenant_id)
        rows = await self._repo.list_agents(
            tenant_id=req.tenant_id, limit=size, skip=pagination.offset(page, size)
        )
        return {
            "list": [_agent_payload(agent, model, tenant.active_agent_id) for agent, model in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def details(self, req: AgentDetailsRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id)
        agent = await self._agent(req.tenant_id, req.id)
        model = (
            await self._models.find_model(agent.model_id) if agent.model_id is not None else None
        )
        tenant = await self._repo.tenant(req.tenant_id)
        assert tenant is not None
        return _agent_payload(agent, model, tenant.active_agent_id)

    async def create(self, req: AgentCreateRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        agent = await self._repo.create_agent(
            tenant_id=req.tenant_id,
            name=_required(req.name, "name", 100),
        )
        await self._session.commit()
        return _agent_payload(agent, None, None)

    async def update(self, req: AgentUpdateRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        tenant = await self._repo.tenant_for_update(req.tenant_id)
        if tenant is None:
            raise ApiError(404, "tenant not found")
        agent = await self._agent(req.tenant_id, req.id)
        changes: dict[str, Any] = {}
        for field in ("model_id", "name", "personality", "system_prompt", "transfer_conditions"):
            if field not in req.model_fields_set:
                continue
            value = getattr(req, field)
            if field == "model_id":
                if value is not None:
                    model = await self._models.find_model(value)
                    if model is None:
                        raise ApiError(404, "model not found")
                    if model.provider.api_provider not in {"openai", "deepseek"}:
                        raise ApiError(400, "model provider is not supported")
                changes[field] = value
            elif field == "name":
                if value is None:
                    raise ApiError(400, "name cannot be null")
                changes[field] = _required(value, field, 100)
            else:
                changes[field] = (value.strip() or None) if value is not None else None
        if not changes:
            raise ApiError(400, "no fields to update")
        if tenant.active_agent_id == agent.id:
            await self._require_ready(agent, changes)
        agent = await self._repo.update_agent(agent, **changes)
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        model = (
            await self._models.find_model(agent.model_id) if agent.model_id is not None else None
        )
        return _agent_payload(agent, model, tenant.active_agent_id)

    async def delete(self, req: AgentDeleteRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        tenant = await self._repo.tenant_for_update(req.tenant_id)
        if tenant is None:
            raise ApiError(404, "tenant not found")
        agent = await self._agent(req.tenant_id, req.id)
        if tenant.active_agent_id == agent.id:
            tenant.active_agent_id = None
            await self._session.flush()
        await self._repo.delete_agent(agent.id)
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        return {
            "id": agent.id,
            "tenant_id": req.tenant_id,
            "active_agent_id": tenant.active_agent_id,
        }

    async def select_active(self, req: AgentSelectRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        tenant = await self._repo.tenant_for_update(req.tenant_id)
        if tenant is None:
            raise ApiError(404, "tenant not found")
        if req.agent_id is not None:
            agent = await self._agent(req.tenant_id, req.agent_id)
            await self._require_ready(agent)
        tenant.active_agent_id = req.agent_id
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        return {"tenant_id": req.tenant_id, "active_agent_id": tenant.active_agent_id}

    async def _require_ready(self, agent: Agent, changes: dict[str, Any] | None = None) -> None:
        values = changes or {}
        model_id = values.get("model_id", agent.model_id)
        if model_id is None:
            raise ApiError(400, "model_id is required for active agent")
        for field in ("system_prompt", "transfer_conditions"):
            value = values.get(field, getattr(agent, field))
            if not value or not value.strip():
                raise ApiError(400, f"{field} is required for active agent")
        model = await self._models.find_model(model_id)
        if model is None:
            raise ApiError(404, "model not found")
        if model.provider.api_provider not in {"openai", "deepseek"}:
            raise ApiError(400, "model provider is not supported")

    async def list_sources(self, req: KnowledgeListRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id)
        await self._agent(req.tenant_id, req.agent_id)
        page, size = pagination.normalize(req.page, req.page_size)
        total = await self._repo.count_sources(req.agent_id)
        rows = await self._repo.list_sources(
            agent_id=req.agent_id, limit=size, skip=pagination.offset(page, size)
        )
        return {
            "list": [_source_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def source_details(self, req: KnowledgeDetailsRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id)
        source = await self._source(req.tenant_id, req.agent_id, req.id)
        return _source_payload(source)

    async def create_source(self, req: KnowledgeCreateRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        await self._agent(req.tenant_id, req.agent_id)
        values = _source_values(req.title, req.kind, req.source_uri, req.content, req.status)
        source = await self._repo.create_source(agent_id=req.agent_id, **values)
        await self._repo.bump_agent_version(req.agent_id)
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        await self._session.refresh(source)
        return _source_payload(source)

    async def update_source(self, req: KnowledgeUpdateRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        source = await self._source(req.tenant_id, req.agent_id, req.id)
        if not (req.model_fields_set & {"title", "kind", "source_uri", "content", "status"}):
            raise ApiError(400, "no fields to update")
        for field in ("title", "kind", "status"):
            if field in req.model_fields_set and getattr(req, field) is None:
                raise ApiError(400, f"{field} cannot be null")
        values = _source_values(
            req.title if "title" in req.model_fields_set else source.title,
            req.kind if "kind" in req.model_fields_set else source.kind,
            req.source_uri if "source_uri" in req.model_fields_set else source.source_uri,
            req.content if "content" in req.model_fields_set else source.content,
            req.status if "status" in req.model_fields_set else source.status,
        )
        for field, value in values.items():
            setattr(source, field, value)
        await self._repo.bump_agent_version(req.agent_id)
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        await self._session.refresh(source)
        return _source_payload(source)

    async def delete_source(self, req: KnowledgeDeleteRequest, token: str) -> dict[str, Any]:
        await self._access(token, req.tenant_id, write=True)
        source = await self._source(req.tenant_id, req.agent_id, req.id)
        await self._repo.delete_source(source)
        await self._repo.bump_agent_version(req.agent_id)
        await self._session.commit()
        await self._cache.delete_agent(req.tenant_id)
        return {"id": req.id, "agent_id": req.agent_id}

    async def _agent(self, tenant_id: str, agent_id: str) -> Agent:
        agent = await self._repo.find_agent(tenant_id=tenant_id, agent_id=_required(agent_id, "id"))
        if agent is None:
            raise ApiError(404, "agent not found")
        return agent

    async def _source(self, tenant_id: str, agent_id: str, source_id: str) -> AgentKnowledgeSource:
        await self._agent(tenant_id, agent_id)
        source = await self._repo.find_source(
            agent_id=agent_id, source_id=_required(source_id, "id")
        )
        if source is None:
            raise ApiError(404, "knowledge source not found")
        return source


def _source_values(
    title: str, kind: str, source_uri: str | None, content: str | None, status: str
) -> dict[str, Any]:
    title = _required(title, "title", 200)
    source_uri = source_uri.strip() if source_uri else None
    content = content.strip() if content else None
    if kind in {"url", "file"} and not source_uri:
        raise ApiError(400, "source_uri is required")
    if kind == "text" and source_uri:
        raise ApiError(400, "source_uri must be empty for text")
    if status == "active" and not content:
        raise ApiError(400, "content is required for active source")
    return {
        "title": title,
        "kind": kind,
        "source_uri": source_uri,
        "content": content,
        "status": status,
    }
