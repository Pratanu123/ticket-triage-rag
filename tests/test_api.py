"""HTTP API smoke tests via FastAPI TestClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agent.classify import ClassificationResult
from app.agent.respond import ResponseResult
from app.models.db import TicketCategory, TicketStatus
from app.rag.retrieve import RetrievedChunk


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "postgres" in body
    assert "chromadb" in body
    assert "ollama" in body
    assert "knowledge_base_docs" in body
    assert body["knowledge_base_docs"] >= 1


def test_post_ticket_returns_201_and_id(client):
    """POST /tickets end-to-end shape; LLM steps stubbed for speed."""
    chunks = [
        RetrievedChunk(
            content="Reset password via Forgot password on the login page.",
            source="login-password-reset.md",
            category="login",
            chunk_index=0,
            score=0.88,
        )
    ]
    classification = ClassificationResult(
        category=TicketCategory.login,
        confidence=0.9,
        reasoning="Clear password reset request.",
        chunks=chunks,
    )
    response_result = ResponseResult(
        status=TicketStatus.auto_resolved,
        suggested_response="Please use Forgot password on the login page.",
        cited_sources=["login-password-reset.md"],
    )

    with (
        patch(
            "app.api.tickets.classify_ticket",
            new=AsyncMock(return_value=classification),
        ),
        patch(
            "app.api.tickets.draft_or_escalate",
            new=AsyncMock(return_value=response_result),
        ),
    ):
        response = client.post(
            "/tickets",
            json={
                "subject": "Password help",
                "body": "I need to reset my password.",
            },
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"]
    assert body["subject"] == "Password help"
    assert body["category"] == "login"
    assert body["status"] == "auto_resolved"


def test_get_ticket_returns_full_record(client):
    chunks = [
        RetrievedChunk(
            content="2FA backup codes can be used to recover access.",
            source="login-2fa.md",
            category="login",
            chunk_index=0,
            score=0.93,
        )
    ]
    classification = ClassificationResult(
        category=TicketCategory.login,
        confidence=0.91,
        reasoning="2FA reset matched login docs.",
        chunks=chunks,
    )
    response_result = ResponseResult(
        status=TicketStatus.auto_resolved,
        suggested_response="Use a backup code, then re-enable 2FA.",
        cited_sources=["login-2fa.md"],
    )

    with (
        patch(
            "app.api.tickets.classify_ticket",
            new=AsyncMock(return_value=classification),
        ),
        patch(
            "app.api.tickets.draft_or_escalate",
            new=AsyncMock(return_value=response_result),
        ),
    ):
        created = client.post(
            "/tickets",
            json={
                "subject": "2FA issue",
                "body": "I cannot log in, 2FA is not working.",
            },
        )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200, response.text
    body = response.json()

    expected_fields = {
        "id",
        "subject",
        "body",
        "category",
        "confidence",
        "status",
        "suggested_response",
        "reasoning",
        "retrieved_chunks",
        "created_at",
        "updated_at",
    }
    assert expected_fields.issubset(body.keys())
    assert body["id"] == ticket_id
    assert body["retrieved_chunks"]
    assert body["retrieved_chunks"][0]["source"] == "login-2fa.md"
    assert body["suggested_response"]
    assert body["reasoning"]


@pytest.mark.llm
def test_post_ticket_live_login_flow(client):
    """One live smoke test through the real classify/respond path."""
    response = client.post(
        "/tickets",
        json={
            "subject": "I cannot log in",
            "body": (
                "I cannot log in, 2FA isn't working after I got a new phone. "
                "How do I reset it?"
            ),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"]
    assert body["category"] == "login"
    assert body["status"] in {"auto_resolved", "needs_human_review"}
    if body["status"] == "auto_resolved":
        assert body["suggested_response"]
        sources = {c["source"] for c in body["retrieved_chunks"]}
        assert any("login" in s for s in sources)
