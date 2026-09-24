# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Please refer to the @CODEBASE_INVENTORY.md to understand current repo tech depth

## Commands

- Install dependencies (including tests): `uv sync --group dev`
- Run the Streamlit app: `uv run streamlit run app.py`
- Index or refresh documents: `uv run python ingest.py`
- Run all tests: `uv run pytest`
- Run one test: `uv run pytest tests/test_ingestion.py::test_new_file_gets_indexed`

There is no build or lint command configured in `pyproject.toml`. Tests cover ingestion behavior and generation model/prompt construction. The app's query pipeline uses a local Ollama model for answer generation; the ingestion pipeline builds the index and does not call Ollama. Start Ollama and pull the configured model (default `gemma2:2b`) before asking questions in the UI. Runtime settings and defaults are in `rag_verify/config.py`; `.env.example` lists the supported environment variables.

## Architecture

`app.py` is the Streamlit client and `ingest.py` is the indexing CLI. Both use `rag_verify`: `RagPipeline` in `rag_verify/pipeline.py` is the shared query entry point, while `rag_verify/ingestion/pipeline.py` owns document indexing.

Ingestion loads supported PDF, DOCX, XLS/XLSX, and Markdown files from `data/raw/`, splits them into chunks, and stores vectors in the persistent Chroma database under `data/chroma_db/`. `data/processed/manifest.json` tracks file hashes and each chunk's text, metadata, and stable ID. The manifest supports incremental indexing, skipping unchanged files and deleting/replacing stale chunk IDs when files change or disappear; it is also the source for the BM25 corpus.

Queries combine BM25 lexical retrieval (useful for exact codes and terms) with Chroma vector retrieval through weighted reciprocal-rank fusion. If there are no manifest chunks yet, retrieval falls back to vector search. `RagPipeline.ask()` limits the fused results to `RETRIEVAL_K`, formats their context with the Ukrainian-language prompt, invokes the configured Ollama chat model, and returns the answer, source names, and chunk count. Embeddings use the configured Hugging Face model (multilingual MiniLM by default); model construction is lazy/cached so ingestion tests do not need to load it.

## Data and configuration

- Put source documents in `data/raw/`; generated index state lives in `data/chroma_db/` and `data/processed/`.
- Configure models, chunking, retrieval count, and BM25 weight with the variables in `.env.example`; defaults are defined in `rag_verify/config.py`.
