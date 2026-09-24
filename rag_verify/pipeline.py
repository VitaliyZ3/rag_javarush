from rag_verify.config import Settings
from rag_verify.generation import build_llm, build_prompt
from rag_verify.retrieval.hybrid import build_retriever


class RagPipeline:
    """Єдина точка входу для UI/CLI — щоб app.py і будь-який інший клієнт
    завжди використовували однакові k, промпт і модель, без дублювання."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.retriever = build_retriever(self.settings)
        self.llm = build_llm(self.settings)
        self.prompt = build_prompt()

    def ask(self, question: str) -> dict:
        # EnsembleRetriever повертає об'єднання обох списків (відсортоване за
        # RRF-скором), а не top-k — тому обрізаємо самі, інакше в промпт
        # летить до 2×k чанків замість запланованого k.
        docs = self.retriever.invoke(question)[: self.settings.retrieval_k]
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        response = self.llm.invoke(self.prompt.format(context=context, question=question))
        sources = sorted({doc.metadata.get("source", "невідомо") for doc in docs})
        return {
            "answer": response.content,
            "sources": sources,
            "chunks_found": len(docs),
        }
