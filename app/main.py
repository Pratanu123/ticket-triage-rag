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
    logger.info("Initializing database schema…")
    await init_db()
    # KB indexing is handled by the one-shot `embed` Compose service before boot.
    logger.info(
        "API ready (ollama=%s model=%s embed=%s collection=%s)",
        settings.ollama_base_url,
        settings.ollama_model,
        settings.ollama_embed_model,
        settings.chroma_collection,
    )
    yield


app = FastAPI(
    title="CloudNova Ticket Triage",
    description=(
        "Fully self-hosted RAG ticket triage using local Ollama "
        "(llama3.1:8b + nomic-embed-text). No external API keys."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(debug.router)
app.include_router(tickets.router)
