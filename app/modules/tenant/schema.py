from pydantic import BaseModel, HttpUrl


class TenantDetailRequest(BaseModel):
    id: str


class TenantCreateRequest(BaseModel):
    name: str
    image_url: HttpUrl | None = None
    legal_name: str | None = None


class TenantUpdateRequest(BaseModel):
    id: str
    name: str | None = None
    image_url: HttpUrl | None = None
    legal_name: str | None = None


class TenantConnectionSubscribeRequest(BaseModel):
    tenant_id: str
    connection_id: str
