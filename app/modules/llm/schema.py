from pydantic import BaseModel, HttpUrl


class ProviderListRequest(BaseModel):
    page: int = 1
    page_size: int = 20


class ProviderCreateRequest(BaseModel):
    api_provider: str
    display_name: str
    image_url: HttpUrl | None = None


class ProviderUpdateRequest(BaseModel):
    id: int
    display_name: str | None = None
    image_url: HttpUrl | None = None


class ModelListRequest(BaseModel):
    page: int = 1
    page_size: int = 20


class ModelCreateRequest(BaseModel):
    provider_id: int
    api_model: str
    display_name: str
    description: str | None = None
