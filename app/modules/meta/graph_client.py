"""Client Graph API untuk memeriksa kesehatan WABA dan nomor WhatsApp milik tenant."""

from typing import Any

import httpx

PHONE_FIELDS = (
    "display_phone_number",
    "verified_name",
    "status",
    "platform_type",
    "is_on_biz_app",
    "quality_rating",
    "code_verification_status",
)


class MetaGraphError(Exception):
    """Graph API menolak atau tidak bisa dihubungi; message-nya aman ditampilkan ke admin."""


class MetaGraphClient:
    def __init__(self, client: httpx.AsyncClient, api_version: str) -> None:
        self._client = client
        self._base_url = f"https://graph.facebook.com/{api_version}"

    async def phone_number(self, *, access_token: str, phone_number_id: str) -> dict[str, Any]:
        return await self._get(
            f"/{phone_number_id}", access_token, params={"fields": ",".join(PHONE_FIELDS)}
        )

    async def subscribed_app_ids(self, *, access_token: str, waba_id: str) -> set[str]:
        data = await self._get(f"/{waba_id}/subscribed_apps", access_token)
        return {
            str(app.get("whatsapp_business_api_data", {}).get("id", ""))
            for app in data.get("data") or []
        }

    async def _get(
        self, path: str, access_token: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            response = await self._client.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        except httpx.HTTPError as exc:
            raise MetaGraphError(f"meta unreachable: {exc.__class__.__name__}") from exc

        try:
            data = response.json()
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if response.is_error:
            err = data.get("error") or {}
            raise MetaGraphError(
                f"({err.get('code', response.status_code)}) {err.get('message', '')}"
            )
        return data
