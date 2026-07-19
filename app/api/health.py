from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.schemas import HealthResponse
from app.rag.embed import count_seed_docs, get_chroma_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    postgres_status = "ok"
    chroma_status = "ok"
    settings = get_settings()

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        postgres_status = f"error: {exc}"

    try:
        heartbeat = get_chroma_client(settings).heartbeat()
        chroma_status = f"ok (heartbeat={heartbeat})"
    except Exception as exc:  # noqa: BLE001
        chroma_status = f"error: {exc}"

    overall = (
        "ok"
        if postgres_status == "ok" and chroma_status.startswith("ok")
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        postgres=postgres_status,
        chromadb=chroma_status,
        knowledge_base_docs=count_seed_docs(settings),
    )
