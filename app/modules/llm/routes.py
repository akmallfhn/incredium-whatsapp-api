from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.routes import bearer_token
from app.modules.llm.schema import (
    ModelCreateRequest,
    ModelListRequest,
    ProviderCreateRequest,
    ProviderListRequest,
    ProviderUpdateRequest,
)
from app.modules.llm.service import LlmService
from app.shared.response import success

ServiceFactory = Callable[[AsyncSession], LlmService]


def register_llm_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/llm", tags=["llm"])

    def service(session: AsyncSession = Depends(get_session)) -> LlmService:
        return build_service(session)

    @router.post("/providers")
    async def providers(
        req: ProviderListRequest,
        token: str = Depends(bearer_token),
        svc: LlmService = Depends(service),
    ) -> Response:
        return success(200, "providers retrieved successfully", await svc.providers(req, token))

    @router.post("/providers/create")
    async def create_provider(
        req: ProviderCreateRequest,
        token: str = Depends(bearer_token),
        svc: LlmService = Depends(service),
    ) -> Response:
        return success(201, "provider created successfully", await svc.create_provider(req, token))

    @router.post("/providers/update")
    async def update_provider(
        req: ProviderUpdateRequest,
        token: str = Depends(bearer_token),
        svc: LlmService = Depends(service),
    ) -> Response:
        return success(200, "provider updated successfully", await svc.update_provider(req, token))

    @router.post("/models")
    async def models(
        req: ModelListRequest,
        token: str = Depends(bearer_token),
        svc: LlmService = Depends(service),
    ) -> Response:
        return success(200, "models retrieved successfully", await svc.models(req, token))

    @router.post("/models/create")
    async def create_model(
        req: ModelCreateRequest,
        token: str = Depends(bearer_token),
        svc: LlmService = Depends(service),
    ) -> Response:
        return success(201, "model created successfully", await svc.create_model(req, token))

    rg.include_router(router)
