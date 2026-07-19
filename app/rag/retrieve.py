"""Query ChromaDB for the top-k most relevant knowledge-base chunks."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config import Settings, get_settings
from app.rag.embed import get_or_create_collection


@dataclass
class RetrievedChunk:
    content: str
    source: str
    category: str
    chunk_index: int
    score: float  # cosine similarity in [0, 1] (higher is better)

    def to_dict(self) -> dict:
        return asdict(self)


def retrieve(
    query: str,
    *,
    k: int | None = None,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    """
    Embed `query` and return the top-k chunks with similarity scores.

    Chroma returns cosine distances when the collection uses hnsw:space=cosine.
    We convert distance → similarity as `1 - distance` for easier reading.
    """
    settings = settings or get_settings()
    top_k = k if k is not None else settings.retrieval_top_k
    if not query or not query.strip():
        return []

    collection = get_or_create_collection(settings)
    raw = collection.query(
        query_texts=[query.strip()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]

    chunks: list[RetrievedChunk] = []
    for doc, meta, distance in zip(documents, metadatas, distances, strict=False):
        meta = meta or {}
        similarity = 1.0 - float(distance)
        chunks.append(
            RetrievedChunk(
                content=doc or "",
                source=str(meta.get("source", "unknown")),
                category=str(meta.get("category", "general")),
                chunk_index=int(meta.get("chunk_index", 0)),
                score=round(similarity, 4),
            )
        )
    return chunks


# Back-compat aliases used by the (existing) triage agent module
retrieve_context = retrieve


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] source={chunk.source} category={chunk.category} "
            f"score={chunk.score:.3f}\n{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)
