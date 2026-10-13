from pydantic import BaseModel


class TenantDetailRequest(BaseModel):
    id: str


class TenantConnectionSubscribeRequest(BaseModel):
    tenant_id: str
    connection_id: str
