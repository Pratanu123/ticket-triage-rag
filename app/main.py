import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import debug, health, tickets
from app.config import get_settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning(
            "OPENAI_API_KEY is empty — local Chroma embeddings are used for "
            "retrieval; LLM triage will fail until a key is set"
        )

    logger.info("Initializing database schema…")
    await init_db()
    # Knowledge-base indexing is handled by the one-shot `embed` Compose service
    # (service_completed_successfully) before this API starts.
    logger.info(
        "API ready (seed_data=%s, collection=%s)",
        settings.seed_data_path,
        settings.chroma_collection,
    )
    yield


app = FastAPI(
    title="CloudNova Ticket Triage",
    description=(
        "RAG-powered support ticket triage. Stage 2: knowledge-base embedding "
        "and retrieval (use POST /debug/retrieve to inspect chunks)."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(debug.router)
app.include_router(tickets.router)
