from collections.abc import Callable

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.routes import bearer_token
from app.modules.patient.schema import (
    CategoryCreateRequest,
    CategoryListRequest,
    PatientConnectRequest,
    PatientCreateRequest,
    PatientIdRequest,
    PatientListRequest,
    PatientUpdateRequest,
)
from app.modules.patient.service import PatientService
from app.shared.response import success

ServiceFactory = Callable[[AsyncSession], PatientService]


def register_patient_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/patients", tags=["patients"])

    def service(session: AsyncSession = Depends(get_session)) -> PatientService:
        return build_service(session)

    category_router = APIRouter(prefix="/patient-categories", tags=["patients"])

    @category_router.post("/create")
    async def create_category(
        req: CategoryCreateRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(
            201, "patient category created successfully", await svc.create_category(req, token)
        )

    @category_router.post("")
    async def categories(
        req: CategoryListRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(
            200, "patient categories retrieved successfully", await svc.categories(req, token)
        )

    rg.include_router(category_router)

    @router.post("/create")
    async def create(
        req: PatientCreateRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(201, "patient created successfully", await svc.create(req, token))

    @router.post("/details")
    async def details(
        req: PatientIdRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(200, "patient retrieved successfully", await svc.details(req, token))

    @router.post("")
    async def list_patients(
        req: PatientListRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(200, "patients retrieved successfully", await svc.list(req, token))

    @router.post("/update")
    async def update(
        req: PatientUpdateRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(200, "patient updated successfully", await svc.update(req, token))

    @router.post("/delete")
    async def delete(
        req: PatientIdRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(200, "patient deleted successfully", await svc.delete(req, token))

    @router.post("/connect-conversation")
    async def connect_conversation(
        req: PatientConnectRequest,
        token: str = Depends(bearer_token),
        svc: PatientService = Depends(service),
    ) -> Response:
        return success(
            200, "patient conversation updated successfully", await svc.connect(req, token)
        )

    rg.include_router(router)
