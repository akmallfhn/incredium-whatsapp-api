from typing import Any

from app.modules.llm.entity import LlmModel, LlmProvider


def provider_payload(provider: LlmProvider) -> dict[str, Any]:
    return {
        "id": provider.id,
        "api_provider": provider.api_provider,
        "display_name": provider.display_name,
        "image_url": provider.image_url,
        "created_at": provider.created_at.isoformat(),
        "updated_at": provider.updated_at.isoformat(),
    }


def model_payload(model: LlmModel) -> dict[str, Any]:
    return {
        "id": model.id,
        "provider_id": model.provider_id,
        "provider_name": model.provider.display_name,
        "api_provider": model.provider.api_provider,
        "provider_image_url": model.provider.image_url,
        "api_model": model.api_model,
        "display_name": model.display_name,
        "description": model.description,
        "created_at": model.created_at.isoformat(),
        "updated_at": model.updated_at.isoformat(),
    }
