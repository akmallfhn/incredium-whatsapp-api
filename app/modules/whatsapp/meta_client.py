"""Client Graph API WhatsApp: unduh attachment dan kirim pesan."""

from typing import Any

import httpx

from app.shared.http import MEDIA_TIMEOUT


class MetaSendError(Exception):
    """Meta menolak pesan; message-nya aman ditampilkan ke admin."""


class MetaMediaClient:
    """Minta metadata media dulu, baru unduh URL-nya."""

    def __init__(self, client: httpx.AsyncClient, api_version: str) -> None:
        self._client = client
        self._api_version = api_version

    async def fetch(
        self, *, access_token: str, phone_number_id: str, media_id: str
    ) -> tuple[bytes, str]:
        info_response = await self._client.get(
            f"https://graph.facebook.com/{self._api_version}/{media_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"phone_number_id": phone_number_id},
            timeout=MEDIA_TIMEOUT,
        )
        info_response.raise_for_status()
        media_info = info_response.json()

        media_url = media_info.get("url")
        if not media_url:
            raise RuntimeError(f"no media url returned for {media_id}: {media_info}")

        download_response = await self._client.get(
            media_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=MEDIA_TIMEOUT,
        )
        download_response.raise_for_status()
        content = download_response.content
        if not content:
            raise RuntimeError(f"empty media download for {media_id}")

        return content, media_info.get("mime_type") or "application/octet-stream"


class MetaMessageClient:
    def __init__(self, client: httpx.AsyncClient, api_version: str) -> None:
        self._client = client
        self._api_version = api_version

    async def send_text(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        to: str,
        body: str,
        reply_to_wam_id: str | None = None,
    ) -> str:
        """Kirim pesan teks dan kembalikan wam_id dari Meta."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        }
        if reply_to_wam_id:
            payload["context"] = {"message_id": reply_to_wam_id}

        try:
            response = await self._client.post(
                f"https://graph.facebook.com/{self._api_version}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise MetaSendError(f"meta unreachable: {exc.__class__.__name__}") from exc

        data = _json_or_empty(response)
        if response.is_error:
            err = data.get("error") or {}
            raise MetaSendError(
                f"({err.get('code', response.status_code)}) {err.get('message', '')}"
            )

        messages = data.get("messages") or []
        if not messages or not messages[0].get("id"):
            raise MetaSendError("meta returned no message id")
        return messages[0]["id"]


def _json_or_empty(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
