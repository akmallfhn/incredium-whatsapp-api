from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.modules.llm.entity import LlmModel, LlmProvider


class LlmRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_providers(self) -> int:
        return (
            await self._session.execute(select(func.count()).select_from(LlmProvider))
        ).scalar_one()

    async def list_providers(self, *, limit: int, skip: int) -> list[LlmProvider]:
        stmt = select(LlmProvider).order_by(LlmProvider.display_name).limit(limit).offset(skip)
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_provider(self, provider_id: int) -> LlmProvider | None:
        return await self._session.get(LlmProvider, provider_id)

    async def create_provider(
        self, *, api_provider: str, display_name: str, image_url: str | None
    ) -> LlmProvider:
        provider = LlmProvider(
            api_provider=api_provider, display_name=display_name, image_url=image_url
        )
        self._session.add(provider)
        await self._session.flush()
        return provider

    async def count_models(self) -> int:
        return (
            await self._session.execute(select(func.count()).select_from(LlmModel))
        ).scalar_one()

    async def list_models(self, *, limit: int, skip: int) -> list[LlmModel]:
        stmt = (
            select(LlmModel)
            .join(LlmProvider, LlmProvider.id == LlmModel.provider_id)
            .options(contains_eager(LlmModel.provider))
            .order_by(LlmProvider.display_name, LlmModel.display_name)
            .limit(limit)
            .offset(skip)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def find_model(self, model_id: int) -> LlmModel | None:
        stmt = (
            select(LlmModel)
            .where(LlmModel.id == model_id)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def create_model(
        self, *, provider_id: int, api_model: str, display_name: str, description: str | None
    ) -> LlmModel:
        model = LlmModel(
            provider_id=provider_id,
            api_model=api_model,
            display_name=display_name,
            description=description,
        )
        self._session.add(model)
        await self._session.flush()
        return model
