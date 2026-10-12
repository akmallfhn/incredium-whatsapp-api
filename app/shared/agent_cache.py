"""Cache Upstash untuk konfigurasi agent dan mode percakapan."""

import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 3600


class AgentCache:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(settings.upstash_redis_rest_url and settings.upstash_redis_rest_token)

    async def _command(self, *parts: Any) -> Any:
        if not self.enabled:
            return None
        try:
            response = await self._client.post(
                settings.upstash_redis_rest_url.rstrip("/"),
                headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
                json=list(parts),
                timeout=3.0,
            )
            response.raise_for_status()
            body = response.json()
            if "error" in body:
                raise RuntimeError(str(body["error"]))
            return body.get("result")
        except Exception:
            logger.exception("agent cache: perintah Upstash gagal")
            return None

    async def get_agent(self, tenant_id: str) -> dict[str, Any] | None:
        value = await self._command("GET", f"agent:tenant:{tenant_id}")
        if not isinstance(value, str):
            return None
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else None
        except ValueError:
            return None

    async def set_agent(self, tenant_id: str, value: dict[str, Any]) -> None:
        await self._command(
            "SET", f"agent:tenant:{tenant_id}", json.dumps(value), "EX", CACHE_TTL_SECONDS
        )

    async def delete_agent(self, tenant_id: str) -> None:
        await self._command("DEL", f"agent:tenant:{tenant_id}")

    async def get_ai_mode(self, conv_id: str) -> bool:
        return await self._command("GET", f"lead:mode:{conv_id}") == "ai"

    async def set_ai_mode(self, conv_id: str) -> None:
        await self._command("SET", f"lead:mode:{conv_id}", "ai", "EX", CACHE_TTL_SECONDS)

    async def delete_mode(self, conv_id: str) -> None:
        await self._command("DEL", f"lead:mode:{conv_id}")
