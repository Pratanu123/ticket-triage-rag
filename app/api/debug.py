from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.retrieve import retrieve

router = APIRouter(prefix="/debug", tags=["debug"])


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Top-k chunks to return (defaults to RETRIEVAL_TOP_K)",
    )


class RetrieveChunkResponse(BaseModel):
    content: str
    source: str
    category: str
    chunk_index: int
    score: float


class RetrieveResponse(BaseModel):
    query: str
    k: int
    chunks: list[RetrieveChunkResponse]


@router.post("/retrieve", response_model=RetrieveResponse)
async def debug_retrieve(payload: RetrieveRequest) -> RetrieveResponse:
    """Temporary endpoint to inspect raw retrieval quality before LLM wiring."""
    settings = get_settings()
    k = payload.k if payload.k is not None else settings.retrieval_top_k
    chunks = retrieve(payload.query, k=k, settings=settings)
    return RetrieveResponse(
        query=payload.query,
        k=k,
        chunks=[RetrieveChunkResponse(**c.to_dict()) for c in chunks],
    )
