from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.entity import Agent, AgentKnowledgeSource, LlmModel
from app.modules.tenant.entity import Tenant
from app.modules.whatsapp.entity import WaChat


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_models(self) -> int:
        return (
            await self._session.execute(select(func.count()).select_from(LlmModel))
        ).scalar_one()

    async def list_models(self, *, limit: int, skip: int) -> list[LlmModel]:
        stmt = (
            select(LlmModel)
            .order_by(LlmModel.provider, LlmModel.display_name)
            .limit(limit)
            .offset(skip)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_model(self, model_id: str) -> LlmModel | None:
        return await self._session.get(LlmModel, model_id)

    async def create_model(self, *, provider: str, api_model: str, display_name: str) -> LlmModel:
        model = LlmModel(provider=provider, api_model=api_model, display_name=display_name)
        self._session.add(model)
        await self._session.flush()
        return model

    async def count_agents(self, tenant_id: str) -> int:
        stmt = select(func.count()).select_from(Agent).where(Agent.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one()

    async def list_agents(
        self, *, tenant_id: str, limit: int, skip: int
    ) -> list[tuple[Agent, LlmModel]]:
        stmt = (
            select(Agent, LlmModel)
            .join(LlmModel, LlmModel.id == Agent.model_id)
            .where(Agent.tenant_id == tenant_id)
            .order_by(Agent.created_at.desc(), Agent.id.desc())
            .limit(limit)
            .offset(skip)
        )
        return list((await self._session.execute(stmt)).all())

    async def find_agent(self, *, tenant_id: str, agent_id: str) -> Agent | None:
        stmt = select(Agent).where(Agent.tenant_id == tenant_id, Agent.id == agent_id).limit(1)
        return (await self._session.execute(stmt)).scalars().first()

    async def create_agent(self, **values: Any) -> Agent:
        agent = Agent(**values)
        self._session.add(agent)
        await self._session.flush()
        return agent

    async def update_agent(self, agent: Agent, **values: Any) -> Agent:
        stmt = (
            update(Agent)
            .where(Agent.id == agent.id, Agent.tenant_id == agent.tenant_id)
            .values(
                **values,
                config_version=Agent.config_version + 1,
                updated_at=func.current_timestamp(),
            )
            .returning(Agent)
        )
        return (
            await self._session.execute(stmt, execution_options={"populate_existing": True})
        ).scalar_one()

    async def tenant_for_update(self, tenant_id: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == tenant_id).with_for_update()
        return (await self._session.execute(stmt)).scalars().first()

    async def tenant(self, tenant_id: str) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def delete_agent(self, agent_id: str) -> None:
        await self._session.execute(
            update(WaChat).where(WaChat.agent_id == agent_id).values(agent_id=None)
        )
        await self._session.execute(
            delete(AgentKnowledgeSource).where(AgentKnowledgeSource.agent_id == agent_id)
        )
        await self._session.execute(delete(Agent).where(Agent.id == agent_id))

    async def count_sources(self, agent_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(AgentKnowledgeSource)
            .where(AgentKnowledgeSource.agent_id == agent_id)
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def list_sources(
        self, *, agent_id: str, limit: int, skip: int
    ) -> list[AgentKnowledgeSource]:
        stmt = (
            select(AgentKnowledgeSource)
            .where(AgentKnowledgeSource.agent_id == agent_id)
            .order_by(AgentKnowledgeSource.created_at.desc(), AgentKnowledgeSource.id.desc())
            .limit(limit)
            .offset(skip)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_source(self, *, agent_id: str, source_id: str) -> AgentKnowledgeSource | None:
        stmt = select(AgentKnowledgeSource).where(
            AgentKnowledgeSource.agent_id == agent_id, AgentKnowledgeSource.id == source_id
        )
        return (await self._session.execute(stmt.limit(1))).scalars().first()

    async def create_source(self, **values: Any) -> AgentKnowledgeSource:
        source = AgentKnowledgeSource(**values)
        self._session.add(source)
        await self._session.flush()
        return source

    async def delete_source(self, source: AgentKnowledgeSource) -> None:
        await self._session.delete(source)

    async def bump_agent_version(self, agent_id: str) -> None:
        await self._session.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(config_version=Agent.config_version + 1, updated_at=func.current_timestamp())
        )

    async def active_sources(self, agent_id: str) -> list[AgentKnowledgeSource]:
        stmt = (
            select(AgentKnowledgeSource)
            .where(
                AgentKnowledgeSource.agent_id == agent_id, AgentKnowledgeSource.status == "active"
            )
            .order_by(AgentKnowledgeSource.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())
