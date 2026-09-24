# Генерація відповідей

## Призначення

Пакет готує мовну модель і prompt для формування відповідей у потоці запитань RAG. **Evidence:** [model.py](model.py), [template.py](template.py), [pipeline.py](../pipeline.py)

Prompt просить відповідати українською на основі знайденого контексту, але сам по собі не перевіряє фактичну точність відповіді. **Evidence:** [template.py](template.py), [pipeline.py](../pipeline.py)

## Залежності

- Інтеграція LangChain з Ollama забезпечує роботу з локальною chat-моделлю. **Evidence:** [model.py](model.py), [pyproject.toml](../../pyproject.toml)
- LangChain Core надає шаблон prompt-а, а вибір моделі й параметри генерації надходять зі спільних налаштувань проєкту. **Evidence:** [template.py](template.py), [model.py](model.py), [config.py](../config.py), [pyproject.toml](../../pyproject.toml)

## Evidence

- [model.py](model.py)
- [template.py](template.py)
- [pipeline.py](../pipeline.py)
- [config.py](../config.py)
- [pyproject.toml](../../pyproject.toml)
