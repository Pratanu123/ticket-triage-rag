import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, tickets
from app.config import get_settings
from app.database import init_db
from app.rag.embeddings import index_knowledge_base, wait_for_chroma

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
            "OPENAI_API_KEY is empty — /health will work, but triage will fail"
        )

    logger.info("Initializing database schema…")
    await init_db()

    logger.info("Waiting for ChromaDB…")
    await wait_for_chroma(settings)

    logger.info("Indexing knowledge base into ChromaDB…")
    indexed = index_knowledge_base(settings)
    logger.info("Startup complete (chunks indexed this boot: %s)", indexed)
    yield


app = FastAPI(
    title="CloudLedger Ticket Triage",
    description=(
        "RAG-powered support ticket classification with confidence-based "
        "human escalation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(tickets.router)
