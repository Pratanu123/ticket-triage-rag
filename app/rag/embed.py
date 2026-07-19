"""Load seed markdown, chunk, embed via Ollama, and upsert into ChromaDB.

Idempotent: chunk IDs are deterministic (`{source}::{chunk_index}`), so re-runs
upsert the same records instead of duplicating them.

Usage:
    python -m app.rag.embed
    python -m app.rag.embed --force
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from pathlib import Path

import chromadb
import httpx
from chromadb.api.models.Collection import Collection
from langchain_ollama import OllamaEmbeddings

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ~500 tokens ≈ 2000 characters for English prose; keep chunks focused.
MAX_CHUNK_CHARS = 2000
SEED_CATEGORY_PREFIXES = {
    "billing": "billing",
    "login": "login",
    "api": "api",
    "faq": "faq",
}


def category_from_filename(filename: str) -> str:
    stem = Path(filename).stem.lower()
    prefix = stem.split("-", 1)[0]
    return SEED_CATEGORY_PREFIXES.get(prefix, "general")


def get_chroma_client(settings: Settings | None = None) -> chromadb.HttpClient:
    settings = settings or get_settings()
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_embeddings(settings: Settings | None = None) -> OllamaEmbeddings:
    """Ollama embeddings (nomic-embed-text by default)."""
    settings = settings or get_settings()
    logger.info(
        "Using Ollama embeddings model=%s base_url=%s",
        settings.ollama_embed_model,
        settings.ollama_base_url,
    )
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def wait_for_chroma(settings: Settings | None = None, attempts: int = 40) -> None:
    settings = settings or get_settings()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            get_chroma_client(settings).heartbeat()
            logger.info("ChromaDB ready (attempt %s)", attempt)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "Waiting for ChromaDB (%s/%s): %s", attempt, attempts, exc
            )
            time.sleep(2)
    raise RuntimeError(
        f"ChromaDB not ready after {attempts} attempts"
    ) from last_error


def wait_for_ollama(settings: Settings | None = None, attempts: int = 60) -> None:
    """Block until Ollama serves the configured embedding model."""
    settings = settings or get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            resp = httpx.get(url, timeout=5.0)
            resp.raise_for_status()
            names = {m.get("name", "") for m in resp.json().get("models", [])}
            # Ollama may report "nomic-embed-text:latest"
            ready = any(
                n == settings.ollama_embed_model
                or n.startswith(f"{settings.ollama_embed_model}:")
                for n in names
            )
            if ready:
                logger.info(
                    "Ollama ready with embed model %s (attempt %s)",
                    settings.ollama_embed_model,
                    attempt,
                )
                return
            logger.warning(
                "Ollama up but %s not pulled yet (%s/%s); models=%s",
                settings.ollama_embed_model,
                attempt,
                attempts,
                sorted(names),
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "Waiting for Ollama (%s/%s): %s", attempt, attempts, exc
            )
        time.sleep(3)
    raise RuntimeError(
        f"Ollama embed model {settings.ollama_embed_model!r} not ready"
    ) from last_error


def _split_oversized(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    parts: list[str] = []
    paragraphs = re.split(r"\n\s*\n", text)
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            parts.append(buf)
        if len(para) <= max_chars:
            buf = para
        else:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf = ""
            for sentence in sentences:
                candidate = f"{buf} {sentence}".strip() if buf else sentence
                if len(candidate) <= max_chars:
                    buf = candidate
                else:
                    if buf:
                        parts.append(buf)
                    buf = sentence[:max_chars]
            if buf:
                parts.append(buf)
                buf = ""
    if buf:
        parts.append(buf)
    return parts


def chunk_markdown(text: str, source: str, category: str) -> list[dict]:
    """Split on ## / ### headings, then size-limit oversized sections."""
    text = text.strip()
    if not text:
        return []

    sections = re.split(r"(?=\n## |\n### )", "\n" + text)
    sections = [s.strip() for s in sections if s.strip()]
    if not sections:
        sections = [text]

    raw_chunks: list[str] = []
    for section in sections:
        raw_chunks.extend(_split_oversized(section))

    results: list[dict] = []
    for index, content in enumerate(raw_chunks):
        results.append(
            {
                "id": f"{source}::{index}",
                "document": content,
                "metadata": {
                    "source": source,
                    "category": category,
                    "chunk_index": index,
                },
            }
        )
    return results


def load_seed_chunks(seed_dir: str | Path) -> list[dict]:
    path = Path(seed_dir)
    if not path.exists():
        raise FileNotFoundError(f"Seed data directory not found: {path}")

    chunks: list[dict] = []
    files = sorted(path.glob("*.md"))
    if not files:
        raise RuntimeError(f"No markdown files found in {path}")

    for md_file in files:
        category = category_from_filename(md_file.name)
        text = md_file.read_text(encoding="utf-8")
        file_chunks = chunk_markdown(text, source=md_file.name, category=category)
        chunks.extend(file_chunks)
        logger.info(
            "Loaded %s → category=%s chunks=%s",
            md_file.name,
            category,
            len(file_chunks),
        )
    return chunks


def get_or_create_collection(
    settings: Settings | None = None,
    *,
    force: bool = False,
) -> Collection:
    """Collection without a server-side embedding fn — we pass vectors explicitly."""
    settings = settings or get_settings()
    client = get_chroma_client(settings)

    if force:
        try:
            client.delete_collection(settings.chroma_collection)
            logger.info("Deleted collection %r", settings.chroma_collection)
        except Exception:  # noqa: BLE001 — may not exist
            pass

    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def count_seed_docs(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return len(list(Path(settings.seed_data_path).glob("*.md")))


def run_embedding_pipeline(
    settings: Settings | None = None,
    *,
    force: bool = False,
) -> dict:
    """Embed seed docs into ChromaDB via Ollama. Safe to re-run (upsert by id)."""
    settings = settings or get_settings()
    wait_for_chroma(settings)
    wait_for_ollama(settings)

    chunks = load_seed_chunks(settings.seed_data_path)
    collection = get_or_create_collection(settings, force=force)
    embedder = get_embeddings(settings)

    batch_size = 16
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        documents = [c["document"] for c in batch]
        vectors = embedder.embed_documents(documents)
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=documents,
            embeddings=vectors,
            metadatas=[c["metadata"] for c in batch],
        )
        logger.info(
            "Upserted batch %s–%s / %s",
            start + 1,
            min(start + batch_size, len(chunks)),
            len(chunks),
        )

    total = collection.count()
    logger.info(
        "Upserted %s chunks from seed_data; collection %r now has %s records",
        len(chunks),
        settings.chroma_collection,
        total,
    )
    return {
        "chunks_upserted": len(chunks),
        "collection_count": total,
        "seed_docs": count_seed_docs(settings),
        "collection": settings.chroma_collection,
        "embed_model": settings.ollama_embed_model,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(description="Index support KB into ChromaDB")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the collection before indexing",
    )
    args = parser.parse_args()
    result = run_embedding_pipeline(force=args.force)
    print(result)


if __name__ == "__main__":
    main()
