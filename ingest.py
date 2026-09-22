import logging

from rag_verify.config import Settings
from rag_verify.ingestion.pipeline import ingest

logging.basicConfig(level=logging.INFO, format="%(message)s")

if __name__ == "__main__":
    ingest(Settings())
