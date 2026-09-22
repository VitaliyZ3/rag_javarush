import json

import pytest

from rag_verify.config import Settings
from rag_verify.ingestion.pipeline import ingest


class FakeVectorStore:
    """Стаб замість Chroma — щоб тестувати diff-логіку без embeddings/torch."""

    def __init__(self):
        self.docs = {}
        self.add_calls = []
        self.delete_calls = []

    def add_documents(self, docs, ids):
        self.add_calls.append(list(ids))
        for doc, doc_id in zip(docs, ids):
            self.docs[doc_id] = doc

    def delete(self, ids):
        self.delete_calls.append(list(ids))
        for doc_id in ids:
            self.docs.pop(doc_id, None)


@pytest.fixture
def settings(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    return Settings(
        data_raw_dir=raw,
        chroma_dir=tmp_path / "chroma_db",
        processed_dir=tmp_path / "processed",
        chunk_size=100,
        chunk_overlap=0,
    )


def test_new_file_gets_indexed(settings):
    (settings.data_raw_dir / "a.md").write_text(
        "Текст про операцію 02302 та поле vehicleState.", encoding="utf-8"
    )
    store = FakeVectorStore()

    stats = ingest(settings, vectorstore=store)

    assert stats == {"added": 1, "updated": 0, "removed": 0, "skipped": 0, "files": 1, "chunks": len(store.docs)}
    assert store.docs
    manifest = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    assert "a.md" in manifest


def test_unchanged_file_is_not_reembedded(settings):
    (settings.data_raw_dir / "a.md").write_text("Текст без змін.", encoding="utf-8")
    store = FakeVectorStore()
    ingest(settings, vectorstore=store)

    stats = ingest(settings, vectorstore=store)  # другий прогін, файл той самий

    assert stats["skipped"] == 1
    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert len(store.add_calls) == 1  # тільки з першого прогону — жодного повторного embedding-виклику


def test_changed_file_replaces_old_chunks(settings):
    path = settings.data_raw_dir / "a.md"
    path.write_text("Версія перша.", encoding="utf-8")
    store = FakeVectorStore()
    ingest(settings, vectorstore=store)
    old_ids = set(store.docs)

    path.write_text("Версія друга, зовсім інший текст.", encoding="utf-8")
    stats = ingest(settings, vectorstore=store)

    assert stats["updated"] == 1
    assert not old_ids & set(store.docs)  # старі id видалені, а не залишились поруч


def test_removed_file_is_deleted_from_index_and_manifest(settings):
    path = settings.data_raw_dir / "a.md"
    path.write_text("Тимчасовий файл.", encoding="utf-8")
    store = FakeVectorStore()
    ingest(settings, vectorstore=store)
    assert store.docs

    path.unlink()
    stats = ingest(settings, vectorstore=store)

    assert stats["removed"] == 1
    assert not store.docs
    manifest = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    assert manifest == {}


def test_duplicate_chunk_content_gets_unique_ids(settings):
    # Реальний баг: RecursiveCharacterTextSplitter може дати кілька однакових
    # коротких чанків (повторювані заголовки/рядки) -> id мають лишатись унікальними.
    (settings.data_raw_dir / "a.md").write_text(
        "Пункт 1.\n\nПункт 1.\n\nПункт 1.\n\nПункт 1.", encoding="utf-8"
    )
    store = FakeVectorStore()

    stats = ingest(settings, vectorstore=store)

    assert stats["added"] == 1
    added_ids = store.add_calls[0]
    assert len(added_ids) == len(set(added_ids))


def test_unsupported_extension_is_skipped(settings):
    (settings.data_raw_dir / "notes.txt").write_text("щось", encoding="utf-8")
    store = FakeVectorStore()

    stats = ingest(settings, vectorstore=store)

    assert stats["files"] == 0
    assert not store.docs
