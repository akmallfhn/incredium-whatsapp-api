from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CategoryCreateRequest(BaseModel):
    tenant_id: str
    name: str


class CategoryListRequest(BaseModel):
    tenant_id: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class PatientFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    satu_sehat_id: str | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    national_id: str | None = None
    bpjs_number: str | None = None
    address: str | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    gender: Literal["male", "female"] | None = None
    blood_type: Literal["A", "B", "AB", "O"] | None = None
    allergy_history: str | None = None


class PatientCreateRequest(PatientFields):
    tenant_id: str
    category_id: int
    name: str
    conversation_id: str | None = None


class PatientUpdateRequest(PatientFields):
    tenant_id: str
    id: str
    category_id: int | None = None
    name: str | None = None


class PatientIdRequest(BaseModel):
    tenant_id: str
    id: str


class PatientListRequest(BaseModel):
    tenant_id: str
    search: str | None = None
    category_id: int | None = None
    conversation_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class PatientConnectRequest(PatientIdRequest):
    conversation_id: str | None
