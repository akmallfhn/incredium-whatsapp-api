"""Factory LLM bersama untuk provider utama yang dipilih."""

from enum import StrEnum
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.core import constants
from app.core.config import settings

DEFAULT_TIMEOUT = 120.0


class Tier(StrEnum):
    """Kelas model yang diminta call site, supaya ganti provider tidak menyentuh modul agent."""

    FAST = "fast"
    FULL = "full"


# Pasangan murah/penuh tiap provider; call site menyebut tier, bukan nama model vendor.
PROVIDER_MODELS: dict[str, dict[str, str]] = {
    "openai": {Tier.FAST: "gpt-4.1-mini", Tier.FULL: "gpt-4.1"},
    "deepseek": {Tier.FAST: "deepseek-flash", Tier.FULL: "deepseek-v4-pro"},
}


def provider() -> str:
    """Provider utama, selalu dari pilihan eksplisit; tidak pernah menebak sendiri."""
    dipilih = (constants.LLM_PROVIDER or "openai").strip().lower()
    if dipilih not in PROVIDER_MODELS:
        raise RuntimeError(
            f"LLM_PROVIDER tidak dikenal: {dipilih}; pilihannya {sorted(PROVIDER_MODELS)}"
        )
    return dipilih


def primary_key() -> str:
    return settings.deepseek_api_key if provider() == "deepseek" else settings.openai_api_key


def is_configured() -> bool:
    """Tanpa satu pun API key semua agent mati; jalur utama aplikasi tetap jalan."""
    return bool(primary_key())


def _primary(tier: Tier, max_tokens: int, timeout: float) -> BaseChatModel:
    nama = provider()
    model = PROVIDER_MODELS[nama][tier]
    if nama == "deepseek":
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=model, api_key=settings.deepseek_api_key, max_tokens=max_tokens, timeout=timeout
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model, api_key=settings.openai_api_key, max_tokens=max_tokens, timeout=timeout
    )


def _prepare(
    llm: BaseChatModel,
    *,
    tools: list[Any] | None,
    structured_output: Any | None,
) -> Runnable:
    """Pasang tool / structured output di tiap provider sesuai cara yang didukungnya."""
    if structured_output is not None:
        return llm.with_structured_output(structured_output, method="json_schema")
    if tools:
        return llm.bind_tools(tools)
    return llm


def build_llm(
    *,
    tier: Tier,
    max_tokens: int,
    timeout: float = DEFAULT_TIMEOUT,
    tools: list[Any] | None = None,
    structured_output: Any | None = None,
) -> Runnable:
    """Runnable siap pakai dari provider utama pada tier yang diminta."""
    if not is_configured():
        raise RuntimeError("API key provider utama wajib diisi untuk agent")
    return _prepare(
        _primary(tier, max_tokens, timeout),
        tools=tools,
        structured_output=structured_output,
    )
