# Генерація відповідей

## Призначення

Пакет готує мовну модель і prompt для формування відповідей у потоці запитань RAG. **Evidence:** [llm.py](llm.py), [prompt.py](prompt.py), [pipeline.py](../pipeline.py)

Prompt просить відповідати українською на основі знайденого контексту, але сам по собі не перевіряє фактичну точність відповіді. **Evidence:** [prompt.py](prompt.py), [pipeline.py](../pipeline.py)

## Залежності

- Інтеграція LangChain з Ollama забезпечує роботу з локальною chat-моделлю. **Evidence:** [llm.py](llm.py), [pyproject.toml](../../pyproject.toml)
- LangChain Core надає шаблон prompt-а, а вибір моделі й параметри генерації надходять зі спільних налаштувань проєкту. **Evidence:** [prompt.py](prompt.py), [llm.py](llm.py), [config.py](../config.py), [pyproject.toml](../../pyproject.toml)

## Evidence

- [llm.py](llm.py)
- [prompt.py](prompt.py)
- [pipeline.py](../pipeline.py)
- [config.py](../config.py)
- [pyproject.toml](../../pyproject.toml)
