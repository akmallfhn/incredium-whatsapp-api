"""Detail tenant beserta kesehatan koneksi WhatsApp-nya, dicek langsung ke Meta."""

import asyncio
from typing import Any

from app.modules.auth.service import AuthService
from app.modules.meta.entity import MetaConnection
from app.modules.meta.graph_client import MetaGraphClient, MetaGraphError
from app.modules.meta.repository import MetaConnectionRepository
from app.modules.tenant.repository import TenantRepository
from app.modules.tenant.schema import TenantDetailRequest
from app.shared.response import ApiError

PHONE_STATUS_CONNECTED = "CONNECTED"


class TenantService:
    def __init__(
        self,
        *,
        auth: AuthService,
        tenants: TenantRepository,
        connections: MetaConnectionRepository,
        graph: MetaGraphClient,
    ) -> None:
        self._auth = auth
        self._tenants = tenants
        self._connections = connections
        self._graph = graph

    async def details(self, req: TenantDetailRequest, token: str) -> dict[str, Any]:
        user = await self._auth.authenticate(token)
        if not req.id.strip():
            raise ApiError(400, "id is required")
        if not any(tenant["id"] == req.id for tenant in user["tenants"]):
            raise ApiError(403, "tenant access denied")
        tenant = await self._tenants.find_by_id(req.id)
        if tenant is None:
            raise ApiError(404, "tenant not found")

        rows = await self._connections.list_by_tenant(tenant.id)
        connections = await asyncio.gather(
            *(self._connection_payload(conn, app_id) for conn, app_id in rows)
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status,
            "active_agent_id": tenant.active_agent_id,
            "connections": list(connections),
        }

    async def _connection_payload(self, conn: MetaConnection, app_id: str) -> dict[str, Any]:
        meta = await self._meta_status(conn, app_id)
        expires_at = conn.token_expires_at
        return {
            "id": conn.id,
            "waba_id": conn.wa_business_id,
            "phone_number_id": conn.wa_phone_number_id,
            # Kolom display_number belum terisi semua; nomor dari Meta jadi cadangannya.
            "display_number": conn.display_number or meta["display_phone_number"],
            "app_id": app_id,
            "status": conn.status,
            "token_expires_at": expires_at.isoformat() if expires_at else None,
            "meta": meta,
        }

    async def _meta_status(self, conn: MetaConnection, app_id: str) -> dict[str, Any]:
        """Gagal ke Meta tidak menggagalkan endpoint; alasannya dikembalikan di field error."""
        status: dict[str, Any] = {
            "connected": False,
            "phone_status": None,
            "platform_type": None,
            "is_on_biz_app": None,
            "coexistence": None,
            "webhook_subscribed": None,
            "display_phone_number": None,
            "verified_name": None,
            "quality_rating": None,
            "error": None,
        }
        if not conn.access_token:
            status["error"] = "access_token is empty"
            return status

        phone, subscribed = await asyncio.gather(
            self._graph.phone_number(
                access_token=conn.access_token, phone_number_id=conn.wa_phone_number_id
            ),
            self._graph.subscribed_app_ids(
                access_token=conn.access_token, waba_id=conn.wa_business_id
            ),
            return_exceptions=True,
        )
        errors = [str(r) for r in (phone, subscribed) if isinstance(r, MetaGraphError)]
        for result in (phone, subscribed):
            if isinstance(result, BaseException) and not isinstance(result, MetaGraphError):
                raise result

        if isinstance(phone, dict):
            status.update(
                phone_status=phone.get("status"),
                platform_type=phone.get("platform_type"),
                is_on_biz_app=phone.get("is_on_biz_app"),
                coexistence=phone.get("platform_type") == "CLOUD_API"
                and phone.get("is_on_biz_app") is True,
                display_phone_number=phone.get("display_phone_number"),
                verified_name=phone.get("verified_name"),
                quality_rating=phone.get("quality_rating"),
            )
        if isinstance(subscribed, set):
            status["webhook_subscribed"] = app_id in subscribed

        status["error"] = "; ".join(errors) or None
        status["connected"] = (
            status["phone_status"] == PHONE_STATUS_CONNECTED
            and status["webhook_subscribed"] is True
        )
        return status
