from functools import lru_cache

from rag_verify.config import Settings


@lru_cache(maxsize=1)
def get_embeddings(settings: Settings):
    # Ліниво: сама модель важка, і не всі виклики (наприклад тести ingestion-логіки) її потребують.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=settings.embed_model,
        model_kwargs={"device": settings.embed_device},
        encode_kwargs={"normalize_embeddings": True},
    )
