from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

GENDER_ENUM = ENUM("male", "female", name="mr_gender_enum", create_type=False)
BLOOD_TYPE_ENUM = ENUM("A", "B", "AB", "O", name="mr_blood_type_enum", create_type=False)


class PatientCategory(Base):
    __tablename__ = "mr_patient_category"
    __table_args__ = (UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "name"))

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))


class Patient(Base):
    __tablename__ = "mr_patients"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "category_id"],
            ["mr_patient_category.tenant_id", "mr_patient_category.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["wa_conversations.tenant_id", "wa_conversations.id"],
        ),
        UniqueConstraint("conversation_id"),
    )

    id: Mapped[str] = mapped_column(CHAR(21), primary_key=True, server_default=text("nanoid()"))
    tenant_id: Mapped[str] = mapped_column(CHAR(21), ForeignKey("tenants.id"))
    category_id: Mapped[int] = mapped_column(BigInteger)
    conversation_id: Mapped[str | None] = mapped_column(CHAR(21))
    name: Mapped[str] = mapped_column(String(255))
    satu_sehat_id: Mapped[str | None] = mapped_column(String)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(String)
    national_id: Mapped[str | None] = mapped_column(String)
    bpjs_number: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(Text)
    phone_number: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    gender: Mapped[str | None] = mapped_column(GENDER_ENUM)
    blood_type: Mapped[str | None] = mapped_column(BLOOD_TYPE_ENUM)
    allergy_history: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
