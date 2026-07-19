"""Load seed markdown, chunk, embed, and upsert into ChromaDB.

Idempotent: chunk IDs are deterministic (`{source}::{chunk_index}`), so re-runs
upsert the same records instead of duplicating them.

Usage:
    python -m app.rag.embed
    python -m app.rag.embed --force   # delete collection first, then re-index
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

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


def get_embedding_function(settings: Settings | None = None):
    """OpenAI when a key is set; otherwise Chroma's local default (onnx)."""
    settings = settings or get_settings()
    if settings.openai_api_key:
        logger.info(
            "Using OpenAI embeddings model=%s", settings.embedding_model
        )
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.embedding_model,
        )

    logger.warning(
        "OPENAI_API_KEY not set — using Chroma DefaultEmbeddingFunction "
        "(local) so indexing still works for retrieval testing"
    )
    return embedding_functions.DefaultEmbeddingFunction()


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
            # Hard wrap very long paragraphs on sentence boundaries.
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

    # Keep the H1 with the first section; split subsequent H2/H3 blocks.
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
    settings = settings or get_settings()
    client = get_chroma_client(settings)
    embedding_fn = get_embedding_function(settings)

    if force:
        try:
            client.delete_collection(settings.chroma_collection)
            logger.info("Deleted collection %r", settings.chroma_collection)
        except Exception:  # noqa: BLE001 — may not exist
            pass

    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=embedding_fn,
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
    """Embed seed docs into ChromaDB. Safe to run repeatedly (upsert by id)."""
    settings = settings or get_settings()
    wait_for_chroma(settings)

    chunks = load_seed_chunks(settings.seed_data_path)
    collection = get_or_create_collection(settings, force=force)

    # Upsert in batches to keep request sizes reasonable
    batch_size = 32
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["document"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
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
