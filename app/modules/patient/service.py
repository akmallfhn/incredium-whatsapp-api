from datetime import date, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.patient.entity import Patient, PatientCategory
from app.modules.patient.repository import PatientRepository
from app.modules.patient.schema import (
    CategoryCreateRequest,
    CategoryListRequest,
    PatientConnectRequest,
    PatientCreateRequest,
    PatientIdRequest,
    PatientListRequest,
    PatientUpdateRequest,
)
from app.shared import pagination
from app.shared.response import ApiError

PATIENT_FIELDS = {
    "satu_sehat_id",
    "birth_date",
    "birth_place",
    "national_id",
    "bpjs_number",
    "address",
    "phone_number",
    "email",
    "gender",
    "blood_type",
    "allergy_history",
}


def _date(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _patient_payload(patient: Patient) -> dict[str, Any]:
    return {
        "id": patient.id,
        "tenant_id": patient.tenant_id,
        "category_id": patient.category_id,
        "conversation_id": patient.conversation_id,
        "name": patient.name,
        "satu_sehat_id": patient.satu_sehat_id,
        "birth_date": _date(patient.birth_date),
        "birth_place": patient.birth_place,
        "national_id": patient.national_id,
        "bpjs_number": patient.bpjs_number,
        "address": patient.address,
        "phone_number": patient.phone_number,
        "email": patient.email,
        "gender": patient.gender,
        "blood_type": patient.blood_type,
        "allergy_history": patient.allergy_history,
        "created_at": _date(patient.created_at),
        "updated_at": _date(patient.updated_at),
    }


def _category_payload(category: PatientCategory) -> dict[str, Any]:
    return {
        "id": category.id,
        "tenant_id": category.tenant_id,
        "name": category.name,
        "created_at": _date(category.created_at),
        "updated_at": _date(category.updated_at),
    }


class PatientService:
    def __init__(
        self, session: AsyncSession, *, auth: AuthService, patients: PatientRepository
    ) -> None:
        self._session = session
        self._auth = auth
        self._patients = patients

    async def _authorize(self, tenant_id: str, token: str) -> None:
        user = await self._auth.authenticate(token)
        if not tenant_id.strip():
            raise ApiError(400, "tenant_id is required")
        if not any(tenant["id"] == tenant_id for tenant in user["tenants"]):
            raise ApiError(403, "tenant access denied")

    async def _check_conversation(
        self, tenant_id: str, conversation_id: str, patient_id: str | None = None
    ) -> None:
        if not conversation_id.strip():
            raise ApiError(400, "conversation_id is required")
        if await self._patients.conversation(tenant_id, conversation_id) is None:
            raise ApiError(404, "conversation not found")
        owner = await self._patients.conversation_owner(conversation_id)
        if owner is not None and owner.id != patient_id:
            raise ApiError(409, "conversation is already connected to another patient")

    async def _commit_conversation(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise ApiError(409, "conversation is already connected to another patient") from exc
            raise

    async def create_category(self, req: CategoryCreateRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        name = req.name.strip()
        if not name:
            raise ApiError(400, "name is required")
        if len(name) > 255:
            raise ApiError(400, "name exceeds 255 characters")
        category = await self._patients.create_category(req.tenant_id, name)
        if category is None:
            raise ApiError(409, "patient category already exists")
        await self._session.commit()
        return _category_payload(category)

    async def categories(self, req: CategoryListRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        page, size = pagination.normalize(req.page, req.page_size)
        total, rows = await self._patients.list_categories(
            req.tenant_id, size, pagination.offset(page, size)
        )
        return {
            "list": [_category_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def create(self, req: PatientCreateRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        name = req.name.strip()
        if not name:
            raise ApiError(400, "name is required")
        if len(name) > 255:
            raise ApiError(400, "name exceeds 255 characters")
        if await self._patients.category(req.tenant_id, req.category_id) is None:
            raise ApiError(404, "patient category not found")
        if req.conversation_id is not None:
            await self._check_conversation(req.tenant_id, req.conversation_id)
        values = req.model_dump(include=PATIENT_FIELDS)
        patient = self._patients.create_patient(
            {
                **values,
                "tenant_id": req.tenant_id,
                "category_id": req.category_id,
                "conversation_id": req.conversation_id,
                "name": name,
            }
        )
        await self._commit_conversation()
        await self._session.refresh(patient)
        return _patient_payload(patient)

    async def details(self, req: PatientIdRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        patient = await self._patients.patient(req.tenant_id, req.id)
        if patient is None:
            raise ApiError(404, "patient not found")
        return _patient_payload(patient)

    async def list(self, req: PatientListRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        page, size = pagination.normalize(req.page, req.page_size)
        total, rows = await self._patients.list_patients(
            req.tenant_id,
            (req.search or "").strip() or None,
            req.category_id,
            size,
            pagination.offset(page, size),
        )
        return {
            "list": [_patient_payload(row) for row in rows],
            "metapaging": pagination.meta(total, page, size),
        }

    async def update(self, req: PatientUpdateRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        fields = req.model_fields_set.intersection(PATIENT_FIELDS | {"name", "category_id"})
        if not fields:
            raise ApiError(400, "at least one field is required")
        patient = await self._patients.patient(req.tenant_id, req.id, lock=True)
        if patient is None:
            raise ApiError(404, "patient not found")
        if "category_id" in fields:
            if req.category_id is None:
                raise ApiError(400, "category_id is required")
            if await self._patients.category(req.tenant_id, req.category_id) is None:
                raise ApiError(404, "patient category not found")
            patient.category_id = req.category_id
        if "name" in fields:
            name = req.name.strip() if req.name is not None else ""
            if not name:
                raise ApiError(400, "name is required")
            if len(name) > 255:
                raise ApiError(400, "name exceeds 255 characters")
            patient.name = name
        for field in fields & PATIENT_FIELDS:
            setattr(patient, field, getattr(req, field))
        await self._session.commit()
        await self._session.refresh(patient)
        return _patient_payload(patient)

    async def delete(self, req: PatientIdRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        patient = await self._patients.patient(req.tenant_id, req.id, lock=True)
        if patient is None:
            raise ApiError(404, "patient not found")
        await self._patients.delete(patient)
        await self._session.commit()
        return {"id": req.id}

    async def connect(self, req: PatientConnectRequest, token: str) -> dict[str, Any]:
        await self._authorize(req.tenant_id, token)
        patient = await self._patients.patient(req.tenant_id, req.id, lock=True)
        if patient is None:
            raise ApiError(404, "patient not found")
        if req.conversation_id is not None:
            await self._check_conversation(req.tenant_id, req.conversation_id, patient.id)
        patient.conversation_id = req.conversation_id
        await self._commit_conversation()
        await self._session.refresh(patient)
        return _patient_payload(patient)
