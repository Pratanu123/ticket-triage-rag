import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import debug, health, tickets
from app.config import get_settings
from app.database import init_db
from app.search.opensearch import ensure_ticket_index

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
    try:
        ensure_ticket_index(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenSearch not ready at startup: %s", exc)
    logger.info(
        "API ready (ollama=%s model=%s embed=%s opensearch=%s:%s)",
        settings.ollama_base_url,
        settings.ollama_model,
        settings.ollama_embed_model,
        settings.opensearch_host,
        settings.opensearch_port,
    )
    yield


app = FastAPI(
    title="CloudNova Ticket Triage",
    description=(
        "Fully self-hosted RAG ticket triage using local Ollama "
        "(llama3.1:8b + nomic-embed-text). Classifies tickets, drafts "
        "replies when confidence is high, and escalates to humans otherwise. "
        "No external API keys."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(health.router)
app.include_router(debug.router)
app.include_router(tickets.router)
