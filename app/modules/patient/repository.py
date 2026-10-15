from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.entity import Patient, PatientCategory
from app.modules.whatsapp.entity import WaConversation


class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def category(self, tenant_id: str, category_id: int) -> PatientCategory | None:
        return await self._session.scalar(
            select(PatientCategory).where(
                PatientCategory.tenant_id == tenant_id, PatientCategory.id == category_id
            )
        )

    async def create_category(self, tenant_id: str, name: str) -> PatientCategory | None:
        stmt = (
            insert(PatientCategory)
            .values(tenant_id=tenant_id, name=name)
            .on_conflict_do_nothing(
                index_elements=[PatientCategory.tenant_id, PatientCategory.name]
            )
            .returning(PatientCategory)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_categories(
        self, tenant_id: str, limit: int, skip: int
    ) -> tuple[int, list[PatientCategory]]:
        condition = PatientCategory.tenant_id == tenant_id
        total = await self._session.scalar(
            select(func.count()).select_from(PatientCategory).where(condition)
        )
        rows = await self._session.scalars(
            select(PatientCategory)
            .where(condition)
            .order_by(PatientCategory.name, PatientCategory.id)
            .limit(limit)
            .offset(skip)
        )
        return total or 0, list(rows)

    async def patient(
        self, tenant_id: str, patient_id: str, *, lock: bool = False
    ) -> Patient | None:
        stmt = select(Patient).where(Patient.tenant_id == tenant_id, Patient.id == patient_id)
        if lock:
            stmt = stmt.with_for_update()
        return await self._session.scalar(stmt)

    def create_patient(self, values: dict) -> Patient:
        patient = Patient(**values)
        self._session.add(patient)
        return patient

    async def list_patients(
        self,
        tenant_id: str,
        search: str | None,
        category_id: int | None,
        conversation_id: str | None,
        limit: int,
        skip: int,
    ) -> tuple[int, list[Patient]]:
        conditions = [Patient.tenant_id == tenant_id]
        if search:
            pattern = f"%{search}%"
            conditions.append(or_(Patient.name.ilike(pattern), Patient.phone_number.ilike(pattern)))
        if category_id is not None:
            conditions.append(Patient.category_id == category_id)
        if conversation_id is not None:
            conditions.append(Patient.conversation_id == conversation_id)
        total = await self._session.scalar(
            select(func.count()).select_from(Patient).where(*conditions)
        )
        rows = await self._session.scalars(
            select(Patient)
            .where(*conditions)
            .order_by(Patient.created_at.desc(), Patient.id.desc())
            .limit(limit)
            .offset(skip)
        )
        return total or 0, list(rows)

    async def conversation(self, tenant_id: str, conversation_id: str) -> WaConversation | None:
        return await self._session.scalar(
            select(WaConversation).where(
                WaConversation.tenant_id == tenant_id, WaConversation.id == conversation_id
            )
        )

    async def conversation_owner(self, conversation_id: str) -> Patient | None:
        return await self._session.scalar(
            select(Patient).where(Patient.conversation_id == conversation_id)
        )

    async def delete(self, patient: Patient) -> None:
        await self._session.delete(patient)
