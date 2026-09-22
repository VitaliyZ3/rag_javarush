from rag_verify.config import Settings
from rag_verify.retrieval.bm25 import build_bm25_retriever
from rag_verify.retrieval.vectorstore import get_vectorstore


def build_retriever(settings: Settings):
    """BM25 (точні терміни/коди на кшталт '02302') + векторний пошук (семантика),
    об'єднані через reciprocal rank fusion. Якщо BM25-корпус ще порожній
    (нічого не проіндексовано) — падає назад на чистий векторний retriever.
    """
    vectorstore = get_vectorstore(settings)
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": settings.retrieval_k})

    bm25_retriever = build_bm25_retriever(settings)
    if bm25_retriever is None:
        return vector_retriever

    try:
        from langchain_classic.retrievers import EnsembleRetriever  # LangChain >= 1.0
    except ImportError:
        from langchain.retrievers import EnsembleRetriever  # LangChain < 1.0

    return EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[settings.bm25_weight, 1 - settings.bm25_weight],
    )
