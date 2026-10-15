import unittest
from types import SimpleNamespace

from app.modules.whatsapp.schema import ConversationListRequest
from app.modules.whatsapp.service import WhatsAppInboxService


class _Auth:
    async def authenticate(self, token: str) -> dict:
        return {"tenants": [{"id": "tenant-a"}]}


class _Tenants:
    def __init__(self, active_agent_id: str | None) -> None:
        self._tenant = SimpleNamespace(active_agent_id=active_agent_id)
        self.calls = 0

    async def find_by_id(self, tenant_id: str) -> SimpleNamespace:
        self.calls += 1
        return self._tenant


class _Conversations:
    async def count_filtered(self, filters: object) -> int:
        return 0

    async def list_filtered(self, filters: object, *, limit: int, skip: int) -> list:
        return []


class WhatsAppConversationMetaPagingTest(unittest.IsolatedAsyncioTestCase):
    async def test_has_active_agent_is_true_when_tenant_has_an_active_agent(self) -> None:
        data, tenants = await self._conversations("agent-a")

        self.assertEqual(tenants.calls, 1)
        self.assertEqual(
            data["metapaging"],
            {
                "total_data": 0,
                "total_page": 0,
                "current_page": 1,
                "page_size": 20,
                "has_active_agent": True,
            },
        )

    async def test_has_active_agent_is_false_for_empty_list_without_active_agent(self) -> None:
        data, tenants = await self._conversations(None)

        self.assertEqual(tenants.calls, 1)
        self.assertEqual(data["list"], [])
        self.assertEqual(
            data["metapaging"],
            {
                "total_data": 0,
                "total_page": 0,
                "current_page": 1,
                "page_size": 20,
                "has_active_agent": False,
            },
        )

    async def _conversations(self, active_agent_id: str | None) -> tuple[dict, _Tenants]:
        tenants = _Tenants(active_agent_id)
        service = WhatsAppInboxService(
            session=SimpleNamespace(),
            auth=_Auth(),
            tenants=tenants,
            connections=SimpleNamespace(),
            conversations=_Conversations(),
            chats=SimpleNamespace(),
            messages=SimpleNamespace(),
            cache=SimpleNamespace(),
        )
        data = await service.conversations(ConversationListRequest(tenant_id="tenant-a"), "token")
        return data, tenants
