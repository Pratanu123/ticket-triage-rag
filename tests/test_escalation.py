"""Escalation gate + human override behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.classify import ClassificationResult
from app.agent.respond import ResponseResult, draft_or_escalate
from app.models.db import TicketCategory, TicketStatus
from app.rag.retrieve import RetrievedChunk


def _fake_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            content="Use backup codes to reset 2FA. See Settings → Security.",
            source="login-2fa.md",
            category="login",
            chunk_index=0,
            score=0.91,
        )
    ]


@pytest.mark.asyncio
async def test_high_confidence_auto_resolves_with_draft():
    """High confidence drafts a reply (response LLM mocked for speed/stability)."""
    classification = ClassificationResult(
        category=TicketCategory.login,
        confidence=0.92,
        reasoning="Clear 2FA reset question matched login docs.",
        chunks=_fake_chunks(),
    )

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=MagicMock(
            content=(
                "You can reset 2FA with a backup code. According to "
                "login-2fa.md, open Settings → Security after signing in."
            )
        )
    )

    with patch("app.agent.respond.get_chat_model", return_value=mock_llm):
        result = await draft_or_escalate(
            "2FA reset",
            "How do I reset my 2FA?",
            classification,
        )

    assert result.status == TicketStatus.auto_resolved
    assert result.suggested_response
    assert "login-2fa.md" in result.cited_sources
    mock_llm.ainvoke.assert_awaited()


@pytest.mark.asyncio
async def test_low_confidence_escalates_without_draft():
    """Low confidence must not call the response LLM or invent a reply."""
    classification = ClassificationResult(
        category=TicketCategory.general,
        confidence=0.2,
        reasoning="Ticket is too vague.",
        chunks=_fake_chunks(),
    )

    with patch("app.agent.respond.get_chat_model") as mock_factory:
        result = await draft_or_escalate(
            "Help",
            "it's broken",
            classification,
        )

    assert result.status == TicketStatus.needs_human_review
    assert result.suggested_response is None
    mock_factory.assert_not_called()


def test_override_updates_escalated_ticket(client):
    """Human-in-the-loop override turns needs_human_review into human_resolved."""
    classification = ClassificationResult(
        category=TicketCategory.general,
        confidence=0.2,
        reasoning="Too vague for auto-resolve",
        chunks=[],
    )
    response_result = ResponseResult(
        status=TicketStatus.needs_human_review,
        suggested_response=None,
        cited_sources=[],
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
            json={"subject": "Ambiguous problem", "body": "it's broken"},
        )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]
    assert created.json()["status"] == "needs_human_review"

    payload = {
        "suggested_response": (
            "Thanks for reporting this — I've looked into it and reset "
            "your workspace flags. Please try again and reply if it persists."
        ),
        "category": "general",
        "note": "Manual review completed",
    }
    response = client.post(f"/tickets/{ticket_id}/override", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["id"] == ticket_id
    assert body["status"] == TicketStatus.human_resolved.value
    assert body["suggested_response"] == payload["suggested_response"]
    assert body["category"] == "general"
    assert "human override" in (body.get("reasoning") or "").lower()
