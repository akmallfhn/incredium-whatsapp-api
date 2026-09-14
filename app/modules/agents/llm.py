"""Factory LLM bersama: OpenAI di depan, Anthropic Haiku cadangan waktu kuotanya habis."""

import logging
from typing import Any

import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0

# Satu model untuk semua node fallback: yang dikejar ketersediaan, bukan kualitas maksimal.
FALLBACK_MODEL = "claude-haiku-4-5-20251001"

# Kegagalan yang tidak berubah kalau diulang ke OpenAI; prompt/schema salah sengaja tidak.
FALLBACK_EXCEPTIONS = (
    openai.RateLimitError,
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.InternalServerError,
    openai.APIConnectionError,
)


def is_configured() -> bool:
    """Tanpa satu pun API key semua agent mati; jalur utama aplikasi tetap jalan."""
    return bool(settings.openai_api_key or settings.anthropic_api_key)


def _openai(model: str, max_tokens: int, timeout: float) -> BaseChatModel:
    # Import lokal supaya langchain_openai tidak wajib ada saat cuma pakai Anthropic.
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _anthropic(max_tokens: int, timeout: float) -> BaseChatModel:
    return ChatAnthropic(
        model=settings.anthropic_fallback_model or FALLBACK_MODEL,
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
    logger.warning("OpenAI tidak bisa dipakai, panggilan dialihkan ke %s", FALLBACK_MODEL)


def build_llm(
    *,
    model: str,
    max_tokens: int,
    timeout: float = DEFAULT_TIMEOUT,
    tools: list[Any] | None = None,
    structured_output: Any | None = None,
) -> Runnable:
    """`model` cuma menamai model OpenAI-nya; cadangannya selalu satu model Haiku."""
    if not is_configured():
        raise RuntimeError("OPENAI_API_KEY atau ANTHROPIC_API_KEY wajib diisi untuk agent")

    def prepare(llm: BaseChatModel) -> Runnable:
        return _prepare(llm, tools=tools, structured_output=structured_output)

    if not settings.openai_api_key:
        return prepare(_anthropic(max_tokens, timeout))

    primary = prepare(_openai(model, max_tokens, timeout))
    if not settings.anthropic_api_key:
        return primary

    fallback = prepare(_anthropic(max_tokens, timeout)).with_listeners(on_start=_log_fallback)
    return primary.with_fallbacks([fallback], exceptions_to_handle=FALLBACK_EXCEPTIONS)
