import sys
from types import ModuleType

from rag_verify.config import Settings
from rag_verify.generation import build_llm, build_prompt


def test_build_llm_uses_settings(monkeypatch):
    calls = []

    def fake_chat_ollama(**kwargs):
        calls.append(kwargs)
        return object()

    ollama_module = ModuleType("langchain_ollama")
    ollama_module.ChatOllama = fake_chat_ollama
    monkeypatch.setitem(sys.modules, "langchain_ollama", ollama_module)

    settings = Settings(
        llm_model="test-model",
        llm_temperature=0.3,
        llm_num_ctx=4096,
        llm_num_predict=256,
    )
    llm = build_llm(settings)

    assert llm is not None
    assert calls == [
        {
            "model": "test-model",
            "temperature": 0.3,
            "num_ctx": 4096,
            "num_predict": 256,
        }
    ]


def test_build_prompt_has_context_and_question_inputs():
    prompt = build_prompt()

    assert set(prompt.input_variables) == {"context", "question"}
    rendered = prompt.format(context="Контекст документа", question="Тестове питання")
    assert "Контекст документа" in rendered
    assert "Тестове питання" in rendered
    assert "Відповідай українською мовою" in rendered
