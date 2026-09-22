import json

from rag_verify.config import Settings


def _load_all_chunks(settings: Settings) -> list:
    from langchain_core.documents import Document

    if not settings.manifest_path.exists():
        return []

    manifest = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    return [
        Document(page_content=c["page_content"], metadata=c["metadata"])
        for entry in manifest.values()
        for c in entry["chunks"]
    ]


def build_bm25_retriever(settings: Settings):
    """Лексичний retriever поверх тих самих чанків, що і в Chroma (manifest.json —
    єдине джерело правди для текстів чанків, без повторного парсингу файлів).
    Повертає None, якщо ще нічого не проіндексовано.
    """
    from langchain_community.retrievers import BM25Retriever

    chunks = _load_all_chunks(settings)
    if not chunks:
        return None

    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = settings.retrieval_k
    return retriever
