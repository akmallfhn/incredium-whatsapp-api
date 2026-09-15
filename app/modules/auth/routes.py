from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.schema import LoginRequest
from app.modules.auth.service import INVALID_TOKEN, AuthService
from app.shared.auth import verify_client_secret
from app.shared.response import ApiError, success

ServiceFactory = Callable[[AsyncSession], AuthService]


def bearer_token(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise ApiError(401, INVALID_TOKEN)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError(401, INVALID_TOKEN)
    return token


def register_auth_routes(rg: APIRouter, build_service: ServiceFactory) -> None:
    router = APIRouter(prefix="/auth", tags=["auth"])

    def service(session: AsyncSession = Depends(get_session)) -> AuthService:
        return build_service(session)

    @router.post("/login", dependencies=[Depends(verify_client_secret)])
    async def login(req: LoginRequest, svc: AuthService = Depends(service)) -> Response:
        return success(200, "login successful", await svc.login(req))

    @router.get("/check-session")
    async def check_session(
        token: str = Depends(bearer_token), svc: AuthService = Depends(service)
    ) -> Response:
        return success(200, "session is valid", await svc.authenticate(token))

    @router.post("/logout")
    async def logout(
        token: str = Depends(bearer_token), svc: AuthService = Depends(service)
    ) -> Response:
        return success(200, "logout successful", await svc.logout(token))

    rg.include_router(router)
