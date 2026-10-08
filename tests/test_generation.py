from __future__ import annotations

import pytest

from rag_verify.config import Settings
from rag_verify.generation.model import build_llm
from rag_verify.generation.template import build_prompt


class FakeChatOllama:
    """Stand-in for langchain_ollama.ChatOllama that just records kwargs."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.model = kwargs.get("model")
        self.temperature = kwargs.get("temperature")
        self.num_ctx = kwargs.get("num_ctx")
        self.num_predict = kwargs.get("num_predict")


def test_build_llm_passes_through_settings(monkeypatch):
    monkeypatch.setattr("langchain_ollama.ChatOllama", FakeChatOllama)

    settings = Settings(
        llm_model="custom-model:1b",
        llm_temperature=0.5,
        llm_num_ctx=1024,
        llm_num_predict=256,
    )

    result = build_llm(settings)

    assert isinstance(result, FakeChatOllama)
    assert result.model == "custom-model:1b"
    assert result.temperature == 0.5
    assert result.num_ctx == 1024
    assert result.num_predict == 256


def test_build_llm_does_not_pass_extra_kwargs(monkeypatch):
    monkeypatch.setattr("langchain_ollama.ChatOllama", FakeChatOllama)

    settings = Settings()
    result = build_llm(settings)

    assert set(result.kwargs.keys()) == {"model", "temperature", "num_ctx", "num_predict"}


def test_build_prompt_input_variables():
    prompt = build_prompt()
    assert prompt.input_variables == ["context", "question"]


def test_build_prompt_formats_context_and_question():
    prompt = build_prompt()
    rendered = prompt.format(context="X", question="Y")

    assert "X" in rendered
    assert "Y" in rendered


def test_build_prompt_contains_ukrainian_fallback_instruction():
    prompt = build_prompt()
    rendered = prompt.format(context="X", question="Y")

    assert "Не знайдено в документах" in rendered
    assert "українською" in rendered.lower()
