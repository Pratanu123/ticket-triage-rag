"""Knowledge-base loading and ChromaDB indexing."""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_vectorstore: Chroma | None = None


def get_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    """Return the configured embedding model (OpenAI today; swappable later)."""
    settings = settings or get_settings()
    if settings.llm_provider != "openai":
        raise ValueError(
            f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. "
            "Currently only 'openai' is implemented."
        )
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def get_chroma_client(settings: Settings | None = None) -> chromadb.HttpClient:
    settings = settings or get_settings()
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_vectorstore(settings: Settings | None = None) -> Chroma:
    global _vectorstore
    settings = settings or get_settings()
    if _vectorstore is None:
        _vectorstore = Chroma(
            client=get_chroma_client(settings),
            collection_name=settings.chroma_collection,
            embedding_function=get_embeddings(settings),
        )
    return _vectorstore


def load_markdown_documents(kb_path: str | Path) -> list[Document]:
    path = Path(kb_path)
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base path not found: {path}")

    documents: list[Document] = []
    for md_file in sorted(path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8").strip()
        if not text:
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={"source": md_file.name, "title": md_file.stem},
            )
        )
    return documents


def count_knowledge_base_docs(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return len(list(Path(settings.knowledge_base_path).glob("*.md")))


async def wait_for_chroma(settings: Settings | None = None, attempts: int = 30) -> None:
    """Block until ChromaDB accepts connections."""
    import asyncio

    settings = settings or get_settings()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            client = get_chroma_client(settings)
            client.heartbeat()
            logger.info("ChromaDB heartbeat ok (attempt %s)", attempt)
            return
        except Exception as exc:  # noqa: BLE001 — retry any connection failure
            last_error = exc
            logger.warning(
                "Waiting for ChromaDB (%s/%s): %s", attempt, attempts, exc
            )
            await asyncio.sleep(2)
    raise RuntimeError(f"ChromaDB not ready after {attempts} attempts") from last_error


def index_knowledge_base(settings: Settings | None = None, *, force: bool = False) -> int:
    """
    Embed and index markdown docs into ChromaDB.

    Skips re-indexing when the collection already has documents, unless force=True.
    Returns the number of chunks indexed (0 if skipped).
    """
    global _vectorstore
    settings = settings or get_settings()
    client = get_chroma_client(settings)

    existing = None
    try:
        existing = client.get_collection(settings.chroma_collection)
        count = existing.count()
        if count > 0 and not force:
            logger.info(
                "Chroma collection %r already has %s docs; skipping re-index",
                settings.chroma_collection,
                count,
            )
            _vectorstore = get_vectorstore(settings)
            return 0
        if force and count > 0:
            client.delete_collection(settings.chroma_collection)
            _vectorstore = None
    except Exception:  # noqa: BLE001 — collection may not exist yet
        pass

    documents = load_markdown_documents(settings.knowledge_base_path)
    if not documents:
        raise RuntimeError(
            f"No markdown documents found in {settings.knowledge_base_path}"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)

    store = Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(settings),
    )
    store.add_documents(chunks)
    _vectorstore = store

    logger.info(
        "Indexed %s chunks from %s source docs into ChromaDB",
        len(chunks),
        len(documents),
    )
    return len(chunks)
