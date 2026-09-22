import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma_db"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"

    embed_model: str = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    embed_device: str = os.getenv("EMBED_DEVICE", "cpu")

    llm_model: str = os.getenv("LLM_MODEL", "gemma2:2b")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "2048"))
    llm_num_predict: int = int(os.getenv("LLM_NUM_PREDICT", "512"))

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    retrieval_k: int = int(os.getenv("RETRIEVAL_K", "6"))
    bm25_weight: float = float(os.getenv("BM25_WEIGHT", "0.4"))

    @property
    def manifest_path(self) -> Path:
        return self.processed_dir / "manifest.json"
