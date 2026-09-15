"""Factory LLM bersama: satu provider utama yang bisa dipilih, Anthropic Haiku cadangannya."""

import logging
from enum import StrEnum
from typing import Any

import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableBinding

from app.core import constants
from app.core.config import settings

logger = logging.getLogger(__name__)

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

# Kegagalan yang tidak berubah kalau diulang ke provider yang sama; prompt/schema salah tidak.
FALLBACK_EXCEPTIONS = (
    openai.RateLimitError,
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.InternalServerError,
    openai.APIConnectionError,
)

# DeepSeek membalas 402 waktu saldonya habis, dan openai SDK tidak punya kelas untuk status itu.
BILLING_STATUS = 402


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
    return bool(primary_key() or settings.anthropic_api_key)


class _MapBillingError(RunnableBinding):
    """Terjemahkan 402 jadi RateLimitError; menangkap APIStatusError apa adanya terlalu lebar."""

    def _translate(self, e: openai.APIStatusError) -> Exception:
        if getattr(e, "status_code", None) != BILLING_STATUS:
            return e
        logger.warning("provider utama menolak dengan %s (saldo habis)", BILLING_STATUS)
        return openai.RateLimitError(str(e), response=e.response, body=e.body)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        try:
            return await super().ainvoke(input, config, **kwargs)
        except openai.APIStatusError as e:
            raise self._translate(e) from e

    async def astream(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        try:
            async for chunk in super().astream(input, config, **kwargs):
                yield chunk
        except openai.APIStatusError as e:
            raise self._translate(e) from e


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


def _anthropic(max_tokens: int, timeout: float) -> BaseChatModel:
    return ChatAnthropic(
        model=constants.ANTHROPIC_FALLBACK_MODEL,
        api_key=settings.anthropic_api_key,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _prepare(
    llm: BaseChatModel,
    *,
    tools: list[Any] | None,
    structured_output: Any | None,
) -> Runnable:
    """Pasang tool / structured output di tiap provider sesuai cara yang didukungnya."""
    if structured_output is not None:
        # Anthropic sengaja tanpa method: default tool call-nya lebih matang dari json_schema.
        if isinstance(llm, ChatAnthropic):
            return llm.with_structured_output(structured_output)
        return llm.with_structured_output(structured_output, method="json_schema")
    if tools:
        return llm.bind_tools(tools)
    return llm


def _log_fallback(*_: Any) -> None:
    logger.warning(
        "%s tidak bisa dipakai, panggilan dialihkan ke %s",
        provider(),
        constants.ANTHROPIC_FALLBACK_MODEL,
    )


def build_llm(
    *,
    tier: Tier,
    max_tokens: int,
    timeout: float = DEFAULT_TIMEOUT,
    tools: list[Any] | None = None,
    structured_output: Any | None = None,
) -> Runnable:
    """Runnable siap pakai; tier memilih model provider utama, cadangannya selalu Haiku."""
    if not is_configured():
        raise RuntimeError("API key provider utama atau ANTHROPIC_API_KEY wajib diisi untuk agent")

    def prepare(llm: BaseChatModel) -> Runnable:
        return _prepare(llm, tools=tools, structured_output=structured_output)

    if not primary_key():
        return prepare(_anthropic(max_tokens, timeout))

    primary = _MapBillingError(bound=prepare(_primary(tier, max_tokens, timeout)))
    if not settings.anthropic_api_key:
        return primary

    fallback = prepare(_anthropic(max_tokens, timeout)).with_listeners(on_start=_log_fallback)
    return primary.with_fallbacks([fallback], exceptions_to_handle=FALLBACK_EXCEPTIONS)
