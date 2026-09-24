from __future__ import annotations

from typing import TYPE_CHECKING

from rag_verify.config import Settings

if TYPE_CHECKING:
    from langchain_ollama import ChatOllama


def build_llm(settings: Settings) -> ChatOllama:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        num_ctx=settings.llm_num_ctx,
        num_predict=settings.llm_num_predict,
    )
