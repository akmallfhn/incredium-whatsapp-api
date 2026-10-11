from pydantic import BaseModel


class TenantDetailRequest(BaseModel):
    id: str
