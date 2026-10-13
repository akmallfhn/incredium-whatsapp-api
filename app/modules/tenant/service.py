"""Detail tenant beserta kesehatan koneksi WhatsApp-nya, dicek langsung ke Meta."""

import asyncio
import re
import secrets
import unicodedata
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.meta.entity import MetaConnection
from app.modules.meta.graph_client import MetaGraphClient, MetaGraphError
from app.modules.meta.repository import MetaConnectionRepository
from app.modules.tenant.entity import STATUS_ACTIVE, Tenant
from app.modules.tenant.repository import TenantRepository
from app.modules.tenant.schema import (
    TenantConnectionSubscribeRequest,
    TenantCreateRequest,
    TenantDetailRequest,
    TenantUpdateRequest,
)
from app.shared.response import ApiError

PHONE_STATUS_CONNECTED = "CONNECTED"
SUBSCRIPTION_ROLES = {"Super Admin", "Administrator"}


def _required_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ApiError(400, "name is required")
    if len(name) > 255:
        raise ApiError(400, "name exceeds 255 characters")
    return name


def _legal_name(value: str | None) -> str | None:
    name = value.strip() if value is not None else None
    if name and len(name) > 255:
        raise ApiError(400, "legal_name exceeds 255 characters")
    return name or None


def _slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:80].rstrip("-") or "tenant"


def _tenant_payload(tenant: Tenant) -> dict[str, Any]:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "image_url": tenant.image_url,
        "legal_name": tenant.legal_name,
        "status": tenant.status,
        "active_agent_id": tenant.active_agent_id,
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat(),
    }


class TenantService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        auth: AuthService,
        tenants: TenantRepository,
        connections: MetaConnectionRepository,
        graph: MetaGraphClient,
    ) -> None:
        self._session = session
        self._auth = auth
        self._tenants = tenants
        self._connections = connections
        self._graph = graph

    async def create(self, req: TenantCreateRequest, token: str) -> dict[str, Any]:
        user = await self._auth.authenticate(token)
        name = _required_name(req.name)
        base_slug = _slug(name)
        for attempt in range(5):
            slug = base_slug if attempt == 0 else f"{base_slug[:71]}-{secrets.token_hex(4)}"
            tenant = await self._tenants.create(
                name=name,
                slug=slug,
                image_url=str(req.image_url) if req.image_url is not None else None,
                legal_name=_legal_name(req.legal_name),
            )
            if tenant is not None:
                self._tenants.grant_access(user_id=user["id"], tenant_id=tenant.id)
                await self._session.commit()
                return _tenant_payload(tenant)
        raise ApiError(409, "tenant slug is unavailable")

    async def update(self, req: TenantUpdateRequest, token: str) -> dict[str, Any]:
        user = await self._auth.authenticate(token)
        if not req.id.strip():
            raise ApiError(400, "id is required")
        if not any(tenant["id"] == req.id for tenant in user["tenants"]):
            raise ApiError(403, "tenant access denied")
        if not req.model_fields_set.intersection({"name", "image_url", "legal_name"}):
            raise ApiError(400, "at least one field is required")
        tenant = await self._tenants.find_by_id(req.id)
        if tenant is None:
            raise ApiError(404, "tenant not found")

        if "name" in req.model_fields_set:
            if req.name is None:
                raise ApiError(400, "name is required")
            tenant.name = _required_name(req.name)
        if "image_url" in req.model_fields_set:
            tenant.image_url = str(req.image_url) if req.image_url is not None else None
        if "legal_name" in req.model_fields_set:
            tenant.legal_name = _legal_name(req.legal_name)
        await self._session.commit()
        await self._session.refresh(tenant)
        return _tenant_payload(tenant)

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
            "image_url": tenant.image_url,
            "legal_name": tenant.legal_name,
            "status": tenant.status,
            "active_agent_id": tenant.active_agent_id,
            "connections": list(connections),
        }

    async def subscribe_connection(
        self, req: TenantConnectionSubscribeRequest, token: str
    ) -> dict[str, Any]:
        user = await self._auth.authenticate(token)
        if not req.tenant_id.strip():
            raise ApiError(400, "tenant_id is required")
        if not req.connection_id.strip():
            raise ApiError(400, "connection_id is required")
        if not any(tenant["id"] == req.tenant_id for tenant in user["tenants"]):
            raise ApiError(403, "tenant access denied")
        if user["role"] not in SUBSCRIPTION_ROLES:
            raise ApiError(403, "connection management denied")

        row = await self._connections.find_by_id_in_tenant(
            tenant_id=req.tenant_id, connection_id=req.connection_id
        )
        if row is None:
            raise ApiError(404, "connection not found")
        conn, app = row
        if conn.status != STATUS_ACTIVE or app.status != STATUS_ACTIVE:
            raise ApiError(409, "connection or Meta app is inactive")
        if not conn.access_token:
            raise ApiError(409, "connection access token is empty")

        try:
            token_app_id = await self._graph.token_app_id(access_token=conn.access_token)
            if token_app_id != app.app_id:
                raise ApiError(409, "access token belongs to another Meta app")
            subscribed_ids = await self._graph.subscribed_app_ids(
                access_token=conn.access_token, waba_id=conn.wa_business_id
            )
            already_subscribed = app.app_id in subscribed_ids
            if not already_subscribed:
                await self._graph.subscribe_app_to_waba(
                    access_token=conn.access_token, waba_id=conn.wa_business_id
                )
                subscribed_ids = await self._graph.subscribed_app_ids(
                    access_token=conn.access_token, waba_id=conn.wa_business_id
                )
                if app.app_id not in subscribed_ids:
                    raise ApiError(502, "Meta did not list the app after subscription")
        except MetaGraphError as exc:
            raise ApiError(502, f"Meta subscription failed: {exc}") from exc

        return {
            "tenant_id": req.tenant_id,
            "connection_id": conn.id,
            "waba_id": conn.wa_business_id,
            "app_id": app.app_id,
            "webhook_subscribed": True,
            "already_subscribed": already_subscribed,
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
