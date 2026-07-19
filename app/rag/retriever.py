"""Retrieval helpers over the indexed knowledge base."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings
from app.rag.embeddings import get_vectorstore


@dataclass
class RetrievedChunk:
    content: str
    source: str
    score: float | None = None


def retrieve_context(
    query: str,
    *,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    k = top_k or settings.retrieval_top_k
    store = get_vectorstore(settings)

    results = store.similarity_search_with_relevance_scores(query, k=k)
    chunks: list[RetrievedChunk] = []
    for doc, score in results:
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                source=str(doc.metadata.get("source", "unknown")),
                score=float(score) if score is not None else None,
            )
        )
    return chunks


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        score_note = f" (score={chunk.score:.3f})" if chunk.score is not None else ""
        parts.append(f"[{i}] source={chunk.source}{score_note}\n{chunk.content}")
    return "\n\n---\n\n".join(parts)
