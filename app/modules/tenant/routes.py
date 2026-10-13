from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.routes import bearer_token
from app.modules.tenant.schema import (
    TenantConnectionSubscribeRequest,
    TenantCreateRequest,
    TenantDetailRequest,
    TenantUpdateRequest,
)
from app.modules.tenant.service import TenantService
from app.shared.response import success

ServiceFactory = Callable[[AsyncSession], TenantService]


def register_tenant_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/tenants", tags=["tenants"])

    def service(session: AsyncSession = Depends(get_session)) -> TenantService:
        return build_service(session)

    @router.post("/create")
    async def create(
        req: TenantCreateRequest,
        token: str = Depends(bearer_token),
        svc: TenantService = Depends(service),
    ) -> Response:
        return success(201, "tenant created successfully", await svc.create(req, token))

    @router.post("/update")
    async def update(
        req: TenantUpdateRequest,
        token: str = Depends(bearer_token),
        svc: TenantService = Depends(service),
    ) -> Response:
        return success(200, "tenant updated successfully", await svc.update(req, token))

    @router.post("/details")
    async def details(
        req: TenantDetailRequest,
        token: str = Depends(bearer_token),
        svc: TenantService = Depends(service),
    ) -> Response:
        return success(200, "tenant retrieved successfully", await svc.details(req, token))

    @router.post("/connections/subscribe")
    async def subscribe_connection(
        req: TenantConnectionSubscribeRequest,
        token: str = Depends(bearer_token),
        svc: TenantService = Depends(service),
    ) -> Response:
        return success(
            200,
            "whatsapp app subscribed successfully",
            await svc.subscribe_connection(req, token),
        )

    rg.include_router(router)
