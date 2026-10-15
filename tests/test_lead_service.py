import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.modules.lead.schema import LeadDetailsRequest, LeadUpdateRequest
from app.modules.lead.service import LeadService


class LeadStagePayloadTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        timestamp = datetime(2026, 10, 15, tzinfo=timezone.utc)
        self.lead = SimpleNamespace(
            conv_id="conversation-a",
            stage_id="stage-a",
            handler_id=None,
            mode="ai",
            note=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.stage = SimpleNamespace(
            id="stage-a",
            name="Qualified",
            description="Lead sudah memenuhi kriteria awal.",
            status="inactive",
        )
        self.session = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())
        self.leads = SimpleNamespace(
            conversation=AsyncMock(return_value=SimpleNamespace(tenant_id="tenant-a")),
            find=AsyncMock(return_value=self.lead),
            lead=AsyncMock(return_value=self.lead),
            stage=AsyncMock(return_value=self.stage),
            stage_by_id=AsyncMock(return_value=self.stage),
        )
        auth = SimpleNamespace(
            authenticate=AsyncMock(return_value={"tenants": [{"id": "tenant-a"}]})
        )
        self.service = LeadService(self.session, auth=auth, leads=self.leads)

    async def test_details_includes_linked_stage_even_when_inactive(self) -> None:
        data = await self.service.details(LeadDetailsRequest(conv_id="conversation-a"), "token")

        self.assertEqual(data["stage_id"], "stage-a")
        self.assertEqual(data["stage_name"], "Qualified")
        self.assertEqual(data["stage_desc"], "Lead sudah memenuhi kriteria awal.")
        self.leads.stage_by_id.assert_awaited_once_with("tenant-a", "stage-a")

    async def test_details_without_stage_returns_null_fields(self) -> None:
        self.lead.stage_id = None

        data = await self.service.details(LeadDetailsRequest(conv_id="conversation-a"), "token")

        self.assertIsNone(data["stage_name"])
        self.assertIsNone(data["stage_desc"])
        self.leads.stage_by_id.assert_not_awaited()

    async def test_update_returns_new_stage_name_and_description(self) -> None:
        self.stage.status = "active"
        data = await self.service.update(
            LeadUpdateRequest(conv_id="conversation-a", stage_id="stage-a"), "token"
        )

        self.assertEqual(data["stage_name"], "Qualified")
        self.assertEqual(data["stage_desc"], "Lead sudah memenuhi kriteria awal.")
        self.leads.stage.assert_awaited_once_with("tenant-a", "stage-a")
        self.leads.stage_by_id.assert_awaited_once_with("tenant-a", "stage-a")
        self.session.commit.assert_awaited_once()

    async def test_update_cleared_stage_returns_null_fields(self) -> None:
        data = await self.service.update(
            LeadUpdateRequest(conv_id="conversation-a", stage_id=None), "token"
        )

        self.assertIsNone(data["stage_id"])
        self.assertIsNone(data["stage_name"])
        self.assertIsNone(data["stage_desc"])
        self.leads.stage.assert_not_awaited()
        self.leads.stage_by_id.assert_not_awaited()
