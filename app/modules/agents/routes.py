from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
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
    ModelCreateRequest,
    ModelListRequest,
)
from app.modules.agents.service import AgentService
from app.modules.auth.routes import bearer_token
from app.shared.response import success

ServiceFactory = Callable[[AsyncSession], AgentService]


def register_agent_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/agents", tags=["agents"])

    def service(session: AsyncSession = Depends(get_session)) -> AgentService:
        return build_service(session)

    @router.post("/models")
    async def models(
        req: ModelListRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(200, "models retrieved successfully", await svc.models(req, token))

    @router.post("/models/create")
    async def create_model(
        req: ModelCreateRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(201, "model created successfully", await svc.create_model(req, token))

    @router.post("/list")
    async def list_agents(
        req: AgentListRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(200, "agents retrieved successfully", await svc.list_agents(req, token))

    @router.post("/details")
    async def details(
        req: AgentDetailsRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(200, "agent retrieved successfully", await svc.details(req, token))

    @router.post("/create")
    async def create(
        req: AgentCreateRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(201, "agent created successfully", await svc.create(req, token))

    @router.post("/update")
    async def update(
        req: AgentUpdateRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(200, "agent updated successfully", await svc.update(req, token))

    @router.post("/delete")
    async def delete(
        req: AgentDeleteRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(200, "agent deleted successfully", await svc.delete(req, token))

    @router.post("/select-active")
    async def select_active(
        req: AgentSelectRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            200, "active agent updated successfully", await svc.select_active(req, token)
        )

    @router.post("/knowledge/list")
    async def list_sources(
        req: KnowledgeListRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            200, "knowledge sources retrieved successfully", await svc.list_sources(req, token)
        )

    @router.post("/knowledge/details")
    async def source_details(
        req: KnowledgeDetailsRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            200, "knowledge source retrieved successfully", await svc.source_details(req, token)
        )

    @router.post("/knowledge/create")
    async def create_source(
        req: KnowledgeCreateRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            201, "knowledge source created successfully", await svc.create_source(req, token)
        )

    @router.post("/knowledge/update")
    async def update_source(
        req: KnowledgeUpdateRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            200, "knowledge source updated successfully", await svc.update_source(req, token)
        )

    @router.post("/knowledge/delete")
    async def delete_source(
        req: KnowledgeDeleteRequest,
        token: str = Depends(bearer_token),
        svc: AgentService = Depends(service),
    ) -> Response:
        return success(
            200, "knowledge source deleted successfully", await svc.delete_source(req, token)
        )

    rg.include_router(router)
