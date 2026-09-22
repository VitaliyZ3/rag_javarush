import hashlib
import json
import logging
from pathlib import Path

from rag_verify.config import Settings
from rag_verify.ingestion.loaders import load_file

logger = logging.getLogger(__name__)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunk_id(source: str, index: int, page_content: str) -> str:
    # index потрібен, щоб не зіштовхнутись на однакових коротких чанках
    # (повторювані заголовки/рядки в документі дають однаковий page_content).
    return hashlib.sha256(f"{source}::{index}::{page_content}".encode("utf-8")).hexdigest()


def _load_manifest(settings: Settings) -> dict:
    if settings.manifest_path.exists():
        return json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    return {}


def _save_manifest(settings: Settings, manifest: dict) -> None:
    settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def ingest(settings: Settings | None = None, vectorstore=None, splitter=None) -> dict:
    """Інкрементальна індексація: перебудовує лише нові/змінені файли,
    видаляє з Chroma чанки видалених/змінених файлів за їхніми стабільними id.
    Ніколи не знищує всю базу — на відміну від попередньої версії.
    """
    settings = settings or Settings()
    settings.data_raw_dir.mkdir(parents=True, exist_ok=True)

    if vectorstore is None:
        from rag_verify.retrieval.vectorstore import get_vectorstore

        vectorstore = get_vectorstore(settings)
    if splitter is None:
        from rag_verify.ingestion.splitter import build_splitter

        splitter = build_splitter(settings)

    manifest = _load_manifest(settings)
    current_files = {p.name: p for p in settings.data_raw_dir.iterdir() if p.is_file()}

    added, updated, removed, skipped = 0, 0, 0, 0

    for name in list(manifest):
        if name not in current_files:
            ids = [c["id"] for c in manifest[name]["chunks"]]
            if ids:
                vectorstore.delete(ids=ids)
            logger.info("Видалено з індексу: %s (%d чанків)", name, len(ids))
            del manifest[name]
            removed += 1

    for name, path in current_files.items():
        new_hash = _file_hash(path)
        old_entry = manifest.get(name)

        if old_entry and old_entry["hash"] == new_hash:
            skipped += 1
            continue

        if old_entry:
            old_ids = [c["id"] for c in old_entry["chunks"]]
            if old_ids:
                vectorstore.delete(ids=old_ids)

        docs = load_file(path)
        if docs is None:
            logger.warning("Пропускаю (немає loader'а для розширення): %s", name)
            continue

        chunks = splitter.split_documents(docs)
        ids = [_chunk_id(name, i, c.page_content) for i, c in enumerate(chunks)]
        if chunks:
            vectorstore.add_documents(chunks, ids=ids)

        manifest[name] = {
            "hash": new_hash,
            "chunks": [
                {"id": cid, "page_content": c.page_content, "metadata": c.metadata}
                for cid, c in zip(ids, chunks)
            ],
        }
        if old_entry:
            updated += 1
        else:
            added += 1
        logger.info("%s: %s (%d чанків)", "Оновлено" if old_entry else "Додано", name, len(chunks))

    _save_manifest(settings, manifest)

    total_chunks = sum(len(v["chunks"]) for v in manifest.values())
    stats = {
        "added": added,
        "updated": updated,
        "removed": removed,
        "skipped": skipped,
        "files": len(manifest),
        "chunks": total_chunks,
    }
    logger.info(
        "Готово. Додано: %d, оновлено: %d, видалено: %d, без змін: %d. "
        "Всього файлів: %d, чанків: %d",
        added, updated, removed, skipped, len(manifest), total_chunks,
    )
    return stats
