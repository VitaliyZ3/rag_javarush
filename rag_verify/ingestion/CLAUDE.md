# Індексація документів

## Призначення

Пакет готує локальні документи до пошуку: завантажує підтримувані файли з каталогу даних, ділить їх на фрагменти й передає до векторного сховища. **Evidence:** [pipeline.py](pipeline.py), [loaders.py](loaders.py), [splitter.py](splitter.py), [../retrieval/vectorstore.py](../retrieval/vectorstore.py)

Індексація оновлює лише додані або змінені документи, пропускає незмінені та прибирає записи видалених документів; її основна точка входу — `ingest()`. **Evidence:** [pipeline.py](pipeline.py)

## Залежності та формати

Завантаження реалізовано через LangChain document loaders, а розбиття тексту — через LangChain text splitter. Підтримуються PDF, DOCX, XLS/XLSX і Markdown; параметри та каталоги беруться зі спільних налаштувань проєкту. **Evidence:** [loaders.py](loaders.py), [splitter.py](splitter.py), [pipeline.py](pipeline.py), [../config.py](../config.py), [../../pyproject.toml](../../pyproject.toml)

Для зберігання фрагментів пакет використовує спільний модуль векторного сховища. Маніфест індексації також є джерелом текстових фрагментів для лексичного пошуку. **Evidence:** [pipeline.py](pipeline.py), [../retrieval/vectorstore.py](../retrieval/vectorstore.py), [../retrieval/bm25.py](../retrieval/bm25.py)

## Evidence

- [pipeline.py](pipeline.py)
- [loaders.py](loaders.py)
- [splitter.py](splitter.py)
- [../config.py](../config.py)
- [../retrieval/vectorstore.py](../retrieval/vectorstore.py)
- [../retrieval/bm25.py](../retrieval/bm25.py)
- [../../pyproject.toml](../../pyproject.toml)
