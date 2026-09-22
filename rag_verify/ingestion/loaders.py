from pathlib import Path

_EXTENSION_LOADERS = {}


def _registry():
    # Ліниво: langchain_community тягне за собою опціональні залежності per-loader.
    if not _EXTENSION_LOADERS:
        from langchain_community.document_loaders import (
            Docx2txtLoader,
            PyPDFLoader,
            TextLoader,
            UnstructuredExcelLoader,
        )

        _EXTENSION_LOADERS.update(
            {
                ".docx": Docx2txtLoader,
                ".xlsx": UnstructuredExcelLoader,
                ".xls": UnstructuredExcelLoader,
                ".pdf": PyPDFLoader,
                ".md": lambda path: TextLoader(path, encoding="utf-8"),
            }
        )
    return _EXTENSION_LOADERS


def load_file(path: Path) -> list | None:
    """Повертає список Document для файлу, або None якщо розширення не підтримується."""
    loader_factory = _registry().get(path.suffix)
    if loader_factory is None:
        return None

    loader = loader_factory(str(path))
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = path.name
    return docs
