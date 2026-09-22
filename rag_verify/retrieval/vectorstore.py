from rag_verify.config import Settings
from rag_verify.embeddings import get_embeddings


def get_vectorstore(settings: Settings):
    from langchain_chroma import Chroma

    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        persist_directory=str(settings.chroma_dir),
        embedding_function=get_embeddings(settings),
    )
