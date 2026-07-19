from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import HealthResponse
from app.rag.embeddings import count_knowledge_base_docs, get_chroma_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    postgres_status = "ok"
    chroma_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        postgres_status = f"error: {exc}"

    try:
        get_chroma_client().heartbeat()
    except Exception as exc:  # noqa: BLE001
        chroma_status = f"error: {exc}"

    overall = (
        "ok"
        if postgres_status == "ok" and chroma_status == "ok"
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        chromadb=chroma_status,
        knowledge_base_docs=count_knowledge_base_docs(),
    )
