# Retrieval

## Призначення

Пакет знаходить релевантні фрагменти документів двома способами: за ключовими словами та за семантичною схожістю. Якщо в маніфесті ще немає фрагментів для лексичного пошуку, використовується лише векторний пошук. **Evidence:** [hybrid.py](hybrid.py), [bm25.py](bm25.py)

BM25 використовує тексти фрагментів і metadata з маніфесту індексації; векторний backend зберігає дані в Chroma та отримує embedding-функцію з пакета `rag_verify`. **Evidence:** [bm25.py](bm25.py), [vectorstore.py](vectorstore.py), [../embeddings.py](../embeddings.py), [../config.py](../config.py)

## Основні залежності

- LangChain retrievers для BM25 і гібридного об'єднання результатів. **Evidence:** [bm25.py](bm25.py), [hybrid.py](hybrid.py), [../../pyproject.toml](../../pyproject.toml)
- ChromaDB через інтеграцію `langchain-chroma` для локального векторного сховища. **Evidence:** [vectorstore.py](vectorstore.py), [../../pyproject.toml](../../pyproject.toml)
- Hugging Face Sentence Transformers через спільну embedding-фабрику для обчислення векторів. **Evidence:** [../embeddings.py](../embeddings.py), [../../pyproject.toml](../../pyproject.toml)

## Evidence

- [hybrid.py](hybrid.py) — побудова гібридного retriever та fallback на векторний пошук.
- [bm25.py](bm25.py) — формування BM25-корпусу з маніфесту.
- [vectorstore.py](vectorstore.py) — створення Chroma vector store.
- [../embeddings.py](../embeddings.py) — embedding-фабрика.
- [../config.py](../config.py) — шляхи та параметри сховища.
- [../../pyproject.toml](../../pyproject.toml) — залежності проєкту.
