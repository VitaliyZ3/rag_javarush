"""Unit tests for the rag_verify.ingestion package.

Covers loaders.load_file, splitter.build_splitter, and the incremental
ingest() pipeline, using tmp_path for all file I/O and fake vectorstores
so no real Chroma/embeddings/Ollama are needed.
"""
import hashlib
import json

import pytest

import rag_verify.ingestion.loaders as loaders_mod
from rag_verify.config import Settings
from rag_verify.ingestion.loaders import load_file
from rag_verify.ingestion.pipeline import ingest
from rag_verify.ingestion.splitter import build_splitter


# ---------------------------------------------------------------------------
# Fakes / helpers
# ---------------------------------------------------------------------------


class FakeDocument:
    """Minimal stand-in for a langchain Document."""

    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class FakeLoader:
    """Fake loader whose factory signature matches real loaders: factory(path)."""

    def __init__(self, path):
        self.path = path

    def load(self):
        return [FakeDocument("fake content A"), FakeDocument("fake content B")]


class FakeVectorStore:
    """Test double tracking add_documents/delete calls."""

    def __init__(self):
        self.added = []  # list of (docs, ids)
        self.deleted = []  # list of ids-lists

    def add_documents(self, docs, ids=None):
        self.added.append((docs, ids))

    def delete(self, ids=None):
        self.deleted.append(ids)


def make_settings(tmp_path, **overrides):
    kwargs = dict(
        data_raw_dir=tmp_path / "raw",
        chroma_dir=tmp_path / "chroma",
        processed_dir=tmp_path / "processed",
    )
    kwargs.update(overrides)
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# loaders.load_file
# ---------------------------------------------------------------------------


def test_load_file_unsupported_extension_returns_none(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello world", encoding="utf-8")

    assert load_file(path) is None


def test_load_file_markdown_uses_real_text_loader(tmp_path):
    path = tmp_path / "doc.md"
    content = "# Title\n\nSome markdown content for testing."
    path.write_text(content, encoding="utf-8")

    docs = load_file(path)

    assert docs is not None
    assert len(docs) == 1
    assert docs[0].page_content == content
    assert docs[0].metadata["source"] == path.name


def test_load_file_dispatches_to_registered_loader_and_stamps_source(
    tmp_path, monkeypatch
):
    fake_path = tmp_path / "report.pdf"
    fake_path.write_bytes(b"not a real pdf")

    # Ensure registry is populated, then override the .pdf entry with our fake.
    loaders_mod._registry()
    monkeypatch.setitem(loaders_mod._EXTENSION_LOADERS, ".pdf", FakeLoader)

    docs = load_file(fake_path)

    assert docs is not None
    assert len(docs) == 2
    assert docs[0].page_content == "fake content A"
    assert docs[1].page_content == "fake content B"
    for doc in docs:
        assert doc.metadata["source"] == fake_path.name


def test_load_file_dispatches_for_docx_and_xlsx_extensions(tmp_path, monkeypatch):
    loaders_mod._registry()
    monkeypatch.setitem(loaders_mod._EXTENSION_LOADERS, ".docx", FakeLoader)
    monkeypatch.setitem(loaders_mod._EXTENSION_LOADERS, ".xlsx", FakeLoader)

    docx_path = tmp_path / "file.docx"
    docx_path.write_bytes(b"fake docx bytes")
    xlsx_path = tmp_path / "file.xlsx"
    xlsx_path.write_bytes(b"fake xlsx bytes")

    for path in (docx_path, xlsx_path):
        docs = load_file(path)
        assert docs is not None
        assert all(doc.metadata["source"] == path.name for doc in docs)


# ---------------------------------------------------------------------------
# splitter.build_splitter
# ---------------------------------------------------------------------------


def test_build_splitter_splits_text_according_to_settings(tmp_path):
    settings = make_settings(tmp_path, chunk_size=50, chunk_overlap=10)
    splitter = build_splitter(settings)

    long_text = " ".join(f"word{i}" for i in range(200))
    chunks = splitter.split_text(long_text)

    assert len(chunks) > 1
    # Chunks should roughly respect the configured chunk_size (allow slack
    # since the splitter avoids breaking words).
    for chunk in chunks:
        assert len(chunk) <= 70


def test_build_splitter_returns_single_chunk_for_short_text(tmp_path):
    settings = make_settings(tmp_path, chunk_size=500, chunk_overlap=50)
    splitter = build_splitter(settings)

    chunks = splitter.split_text("short text")

    assert chunks == ["short text"]


# ---------------------------------------------------------------------------
# pipeline.ingest
# ---------------------------------------------------------------------------


def test_ingest_first_run_adds_file(tmp_path):
    settings = make_settings(tmp_path)
    settings.data_raw_dir.mkdir(parents=True)
    (settings.data_raw_dir / "a.md").write_text("Hello world, this is a test.", encoding="utf-8")

    vectorstore = FakeVectorStore()
    splitter = build_splitter(settings)

    stats = ingest(settings=settings, vectorstore=vectorstore, splitter=splitter)

    assert stats["added"] == 1
    assert stats["updated"] == 0
    assert stats["removed"] == 0
    assert stats["skipped"] == 0
    assert stats["files"] == 1

    assert settings.manifest_path.exists()
    manifest = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    assert "a.md" in manifest
    expected_hash = hashlib.sha256(
        (settings.data_raw_dir / "a.md").read_bytes()
    ).hexdigest()
    assert manifest["a.md"]["hash"] == expected_hash
    assert len(manifest["a.md"]["chunks"]) == stats["chunks"]
    assert manifest["a.md"]["chunks"][0]["page_content"]

    assert len(vectorstore.added) == 1
    assert len(vectorstore.deleted) == 0
    # The ids handed to the vector store must match the ids persisted in
    # the manifest, otherwise later delete-on-change calls would orphan
    # vectors that the manifest no longer references.
    added_ids = vectorstore.added[0][1]
    assert added_ids == [c["id"] for c in manifest["a.md"]["chunks"]]


def test_ingest_second_run_with_no_changes_skips(tmp_path):
    settings = make_settings(tmp_path)
    settings.data_raw_dir.mkdir(parents=True)
    (settings.data_raw_dir / "a.md").write_text("Hello world, this is a test.", encoding="utf-8")

    splitter = build_splitter(settings)

    vectorstore1 = FakeVectorStore()
    ingest(settings=settings, vectorstore=vectorstore1, splitter=splitter)

    vectorstore2 = FakeVectorStore()
    stats = ingest(settings=settings, vectorstore=vectorstore2, splitter=splitter)

    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["removed"] == 0
    assert stats["skipped"] == 1

    assert vectorstore2.added == []
    assert vectorstore2.deleted == []


def test_ingest_modified_file_updates(tmp_path):
    settings = make_settings(tmp_path)
    settings.data_raw_dir.mkdir(parents=True)
    file_path = settings.data_raw_dir / "a.md"
    file_path.write_text("Hello world, this is a test.", encoding="utf-8")

    splitter = build_splitter(settings)

    vs1 = FakeVectorStore()
    ingest(settings=settings, vectorstore=vs1, splitter=splitter)

    manifest_before = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    old_ids = [c["id"] for c in manifest_before["a.md"]["chunks"]]

    file_path.write_text("Completely different content now, much longer than before.", encoding="utf-8")

    vs2 = FakeVectorStore()
    stats = ingest(settings=settings, vectorstore=vs2, splitter=splitter)

    assert stats["added"] == 0
    assert stats["updated"] == 1
    assert stats["removed"] == 0
    assert stats["skipped"] == 0

    assert len(vs2.deleted) == 1
    assert vs2.deleted[0] == old_ids

    assert len(vs2.added) == 1

    manifest_after = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    new_ids = [c["id"] for c in manifest_after["a.md"]["chunks"]]
    assert new_ids != old_ids
    assert manifest_after["a.md"]["hash"] != manifest_before["a.md"]["hash"]


def test_ingest_removed_file_deletes_from_manifest_and_store(tmp_path):
    settings = make_settings(tmp_path)
    settings.data_raw_dir.mkdir(parents=True)
    file_path = settings.data_raw_dir / "a.md"
    file_path.write_text("Hello world, this is a test.", encoding="utf-8")

    splitter = build_splitter(settings)

    vs1 = FakeVectorStore()
    ingest(settings=settings, vectorstore=vs1, splitter=splitter)

    manifest_before = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    old_ids = [c["id"] for c in manifest_before["a.md"]["chunks"]]

    file_path.unlink()

    vs2 = FakeVectorStore()
    stats = ingest(settings=settings, vectorstore=vs2, splitter=splitter)

    assert stats["added"] == 0
    assert stats["updated"] == 0
    assert stats["removed"] == 1
    assert stats["skipped"] == 0
    assert stats["files"] == 0

    assert len(vs2.deleted) == 1
    assert vs2.deleted[0] == old_ids
    assert vs2.added == []

    manifest_after = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    assert "a.md" not in manifest_after


def test_ingest_skips_unsupported_extension_silently(tmp_path):
    settings = make_settings(tmp_path)
    settings.data_raw_dir.mkdir(parents=True)
    (settings.data_raw_dir / "ignored.txt").write_text("not indexed", encoding="utf-8")

    vectorstore = FakeVectorStore()
    splitter = build_splitter(settings)

    stats = ingest(settings=settings, vectorstore=vectorstore, splitter=splitter)

    assert stats["added"] == 0
    assert stats["files"] == 0
    assert vectorstore.added == []
    assert vectorstore.deleted == []

    manifest = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    assert manifest == {}
