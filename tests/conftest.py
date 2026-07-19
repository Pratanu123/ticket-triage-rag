"""Shared fixtures. Tests are meant to run inside Compose against real services:

    docker compose run --rm api pytest -v
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.rag.embed import get_chroma_client, run_embedding_pipeline

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def ensure_knowledge_base(settings):
    """Make sure Chroma has seed chunks (idempotent upsert if empty/missing)."""
    try:
        client = get_chroma_client(settings)
        client.heartbeat()
        try:
            count = client.get_collection(settings.chroma_collection).count()
        except Exception:  # noqa: BLE001
            count = 0
        if count == 0:
            logger.info("Chroma empty — running embedding pipeline for tests")
            run_embedding_pipeline(settings)
        else:
            logger.info("Chroma already has %s chunks", count)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ChromaDB / Ollama not available for tests: {exc}")


@pytest.fixture(scope="session")
def client(ensure_knowledge_base):
    """Sync TestClient; lifespan initializes Postgres schema."""
    with TestClient(app) as test_client:
        yield test_client
