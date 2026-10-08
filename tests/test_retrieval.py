import json

import pytest
from langchain_core.retrievers import BaseRetriever

from rag_verify.config import Settings
from rag_verify.retrieval import bm25, hybrid, vectorstore


def make_settings(tmp_path, **overrides):
    kwargs = dict(
        data_raw_dir=tmp_path / "raw",
        chroma_dir=tmp_path / "chroma",
        processed_dir=tmp_path / "processed",
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


def write_manifest(settings: Settings, manifest: dict):
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


SAMPLE_MANIFEST = {
    "file.md": {
        "hash": "deadbeef",
        "chunks": [
            {
                "id": "file.md::0",
                "page_content": "Полиморфизм - це основний принцип ООП в Java.",
                "metadata": {"source": "file.md", "chunk_index": 0},
            },
            {
                "id": "file.md::1",
                "page_content": "Інкапсуляція приховує внутрішню реалізацію класу.",
                "metadata": {"source": "file.md", "chunk_index": 1},
            },
        ],
    }
}


# ---------------------------------------------------------------------------
# bm25._load_all_chunks
# ---------------------------------------------------------------------------


class TestLoadAllChunks:
    def test_no_manifest_returns_empty_list(self, tmp_path):
        settings = make_settings(tmp_path)
        assert bm25._load_all_chunks(settings) == []

    def test_manifest_with_chunks_returns_documents(self, tmp_path):
        settings = make_settings(tmp_path)
        write_manifest(settings, SAMPLE_MANIFEST)

        docs = bm25._load_all_chunks(settings)

        assert len(docs) == 2
        expected_chunks = SAMPLE_MANIFEST["file.md"]["chunks"]
        for doc, expected in zip(docs, expected_chunks):
            assert doc.page_content == expected["page_content"]
            assert doc.metadata == expected["metadata"]


# ---------------------------------------------------------------------------
# bm25.build_bm25_retriever
# ---------------------------------------------------------------------------


class TestBuildBm25Retriever:
    def test_missing_manifest_returns_none(self, tmp_path):
        settings = make_settings(tmp_path)
        assert bm25.build_bm25_retriever(settings) is None

    def test_empty_manifest_returns_none(self, tmp_path):
        settings = make_settings(tmp_path)
        write_manifest(settings, {})
        assert bm25.build_bm25_retriever(settings) is None

    def test_manifest_with_chunks_builds_real_retriever(self, tmp_path):
        settings = make_settings(tmp_path, retrieval_k=3)
        write_manifest(settings, SAMPLE_MANIFEST)

        retriever = bm25.build_bm25_retriever(settings)

        assert retriever is not None
        assert retriever.k == 3

        results = retriever.invoke("Полиморфизм ООП Java")
        assert len(results) >= 1
        assert any(
            doc.page_content == SAMPLE_MANIFEST["file.md"]["chunks"][0]["page_content"]
            for doc in results
        )

    def test_manifest_with_chunks_ranks_best_match_first(self, tmp_path):
        # BM25's idf collapses to ~0 (a tie) when a term appears in exactly
        # one of only two documents, so a 2-doc corpus can't reliably assert
        # ranking order. Use a 3-doc corpus where idf for a distinguishing
        # term is unambiguously positive, to actually exercise ranking.
        ranking_manifest = {
            "file.md": {
                "hash": "deadbeef",
                "chunks": [
                    {
                        "id": "file.md::0",
                        "page_content": "Полиморфизм - це основний принцип ООП в Java",
                        "metadata": {"source": "file.md", "chunk_index": 0},
                    },
                    {
                        "id": "file.md::1",
                        "page_content": "Інкапсуляція приховує внутрішню реалізацію класу",
                        "metadata": {"source": "file.md", "chunk_index": 1},
                    },
                    {
                        "id": "file.md::2",
                        "page_content": "Спадкування дозволяє класу успадкувати поведінку батьківського класу",
                        "metadata": {"source": "file.md", "chunk_index": 2},
                    },
                ],
            }
        }
        settings = make_settings(tmp_path, retrieval_k=3)
        write_manifest(settings, ranking_manifest)

        retriever = bm25.build_bm25_retriever(settings)

        results = retriever.invoke("Полиморфизм ООП Java")
        assert len(results) >= 1
        assert results[0].page_content == ranking_manifest["file.md"]["chunks"][0]["page_content"]


# ---------------------------------------------------------------------------
# hybrid.build_retriever
# ---------------------------------------------------------------------------


class SentinelRetriever(BaseRetriever):
    """Minimal real BaseRetriever so it survives EnsembleRetriever's pydantic
    validation (a bare object() fails validation since retrievers must be
    Runnable)."""

    def _get_relevant_documents(self, query, *, run_manager=None):
        return []


class FakeVectorStore:
    def __init__(self):
        self.as_retriever_calls = []

    def as_retriever(self, search_kwargs=None):
        self.as_retriever_calls.append(search_kwargs)
        return VECTOR_SENTINEL


VECTOR_SENTINEL = SentinelRetriever()
BM25_SENTINEL = SentinelRetriever()


class TestBuildRetriever:
    def test_falls_back_to_vector_retriever_when_no_bm25(self, tmp_path, monkeypatch):
        settings = make_settings(tmp_path, retrieval_k=5, bm25_weight=0.4)
        fake_vectorstore = FakeVectorStore()

        monkeypatch.setattr(hybrid, "get_vectorstore", lambda s: fake_vectorstore)
        monkeypatch.setattr(hybrid, "build_bm25_retriever", lambda s: None)

        result = hybrid.build_retriever(settings)

        assert result is VECTOR_SENTINEL
        assert fake_vectorstore.as_retriever_calls == [{"k": 5}]

    def test_combines_bm25_and_vector_into_ensemble(self, tmp_path, monkeypatch):
        settings = make_settings(tmp_path, retrieval_k=5, bm25_weight=0.4)
        fake_vectorstore = FakeVectorStore()

        monkeypatch.setattr(hybrid, "get_vectorstore", lambda s: fake_vectorstore)
        monkeypatch.setattr(hybrid, "build_bm25_retriever", lambda s: BM25_SENTINEL)

        result = hybrid.build_retriever(settings)

        try:
            from langchain_classic.retrievers import EnsembleRetriever
        except ImportError:
            from langchain.retrievers import EnsembleRetriever

        assert isinstance(result, EnsembleRetriever)
        assert result.retrievers == [BM25_SENTINEL, VECTOR_SENTINEL]
        assert result.retrievers[0] is BM25_SENTINEL
        assert result.retrievers[1] is VECTOR_SENTINEL
        assert result.weights == pytest.approx([0.4, 0.6])
        assert fake_vectorstore.as_retriever_calls == [{"k": 5}]


# ---------------------------------------------------------------------------
# vectorstore.get_vectorstore
# ---------------------------------------------------------------------------


class FakeChroma:
    last_kwargs = None
    instance = None

    def __init__(self, **kwargs):
        FakeChroma.last_kwargs = kwargs
        FakeChroma.instance = self


class TestGetVectorstore:
    def test_creates_chroma_dir_and_constructs_chroma(self, tmp_path, monkeypatch):
        settings = make_settings(tmp_path)
        assert not settings.chroma_dir.exists()

        fake_embeddings = object()
        monkeypatch.setattr(vectorstore, "get_embeddings", lambda s: fake_embeddings)

        import langchain_chroma

        FakeChroma.last_kwargs = None
        FakeChroma.instance = None
        monkeypatch.setattr(langchain_chroma, "Chroma", FakeChroma)

        result = vectorstore.get_vectorstore(settings)

        assert settings.chroma_dir.exists()
        assert FakeChroma.last_kwargs["persist_directory"] == str(settings.chroma_dir)
        assert FakeChroma.last_kwargs["embedding_function"] is fake_embeddings
        assert result is FakeChroma.instance
