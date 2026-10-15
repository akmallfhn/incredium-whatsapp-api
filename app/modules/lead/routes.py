from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.routes import bearer_token
from app.modules.lead.schema import (
    LeadChangeModeRequest,
    LeadDetailsRequest,
    LeadStageListRequest,
    LeadUpdateRequest,
)
from app.modules.lead.service import LeadService
from app.shared.response import success

ServiceFactory = Callable[[AsyncSession], LeadService]


def register_lead_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/leads", tags=["leads"])

    def service(session: AsyncSession = Depends(get_session)) -> LeadService:
        return build_service(session)

    @router.post("/change-mode")
    async def change_mode(
        req: LeadChangeModeRequest,
        token: str = Depends(bearer_token),
        svc: LeadService = Depends(service),
    ) -> Response:
        return success(200, "lead mode updated successfully", await svc.change_mode(req, token))

    @router.post("/details")
    async def details(
        req: LeadDetailsRequest,
        token: str = Depends(bearer_token),
        svc: LeadService = Depends(service),
    ) -> Response:
        return success(200, "lead retrieved successfully", await svc.details(req, token))

    @router.post("/update")
    async def update(
        req: LeadUpdateRequest,
        token: str = Depends(bearer_token),
        svc: LeadService = Depends(service),
    ) -> Response:
        return success(200, "lead updated successfully", await svc.update(req, token))

    rg.include_router(router)

    stage_router = APIRouter(prefix="/lead-stages", tags=["leads"])

    @stage_router.post("")
    async def stages(
        req: LeadStageListRequest,
        token: str = Depends(bearer_token),
        svc: LeadService = Depends(service),
    ) -> Response:
        return success(200, "lead stages retrieved successfully", await svc.stages(req, token))

    rg.include_router(stage_router)
