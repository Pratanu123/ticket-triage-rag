"""OpenSearch audit index for searchable ticket history."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from opensearchpy import OpenSearch, NotFoundError

from app.config import Settings, get_settings
from app.models.db import Ticket

logger = logging.getLogger(__name__)

TICKETS_INDEX = "support_tickets"

INDEX_BODY = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index": {"refresh_interval": "1s"},
    },
    "mappings": {
        "properties": {
            "ticket_id": {"type": "keyword"},
            "subject": {"type": "text"},
            "body": {"type": "text"},
            "category": {"type": "keyword"},
            "confidence": {"type": "float"},
            "status": {"type": "keyword"},
            "reasoning": {"type": "text"},
            "suggested_response": {"type": "text"},
            "event": {"type": "keyword"},
            "timestamp": {"type": "date"},
        }
    },
}


def get_opensearch_client(settings: Settings | None = None) -> OpenSearch:
    settings = settings or get_settings()
    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=30,
    )


def ensure_ticket_index(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = get_opensearch_client(settings)
    try:
        if not client.indices.exists(index=TICKETS_INDEX):
            client.indices.create(index=TICKETS_INDEX, body=INDEX_BODY)
            logger.info("Created OpenSearch index %s", TICKETS_INDEX)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenSearch index ensure failed: %s", exc)


def ticket_document(ticket: Ticket, *, event: str) -> dict[str, Any]:
    ts = ticket.updated_at or ticket.created_at or datetime.utcnow()
    if ts.tzinfo is None:
        timestamp = ts.isoformat() + "Z"
    else:
        timestamp = ts.isoformat()
    return {
        "ticket_id": str(ticket.id),
        "subject": ticket.subject,
        "body": ticket.body,
        "category": ticket.category.value if ticket.category else None,
        "confidence": float(ticket.confidence or 0.0),
        "status": ticket.status.value if ticket.status else None,
        "reasoning": ticket.reasoning,
        "suggested_response": ticket.suggested_response,
        "event": event,
        "timestamp": timestamp,
    }


def index_ticket(ticket: Ticket, *, event: str, settings: Settings | None = None) -> None:
    """Best-effort index/update of a ticket audit document."""
    settings = settings or get_settings()
    try:
        client = get_opensearch_client(settings)
        ensure_ticket_index(settings)
        doc = ticket_document(ticket, event=event)
        client.index(
            index=TICKETS_INDEX,
            id=str(ticket.id),
            body=doc,
            refresh=True,
        )
    except Exception as exc:  # noqa: BLE001 — search must not break triage
        logger.warning("Failed to index ticket %s into OpenSearch: %s", ticket.id, exc)


def search_tickets(
    query: str,
    *,
    size: int = 20,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    client = get_opensearch_client(settings)
    ensure_ticket_index(settings)

    q = (query or "").strip()
    if not q:
        body = {
            "size": size,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"match_all": {}},
        }
    else:
        body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": ["subject^3", "body", "reasoning", "category", "status"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
        }

    try:
        result = client.search(index=TICKETS_INDEX, body=body)
    except NotFoundError:
        return []

    hits = []
    for hit in result.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        source["_score"] = hit.get("_score")
        hits.append(source)
    return hits


def get_indexed_ticket(ticket_id: UUID | str, settings: Settings | None = None) -> dict | None:
    settings = settings or get_settings()
    client = get_opensearch_client(settings)
    try:
        return client.get(index=TICKETS_INDEX, id=str(ticket_id)).get("_source")
    except NotFoundError:
        return None
