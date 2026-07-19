"""Classification against the real local Ollama chat model (small, focused set)."""

from __future__ import annotations

import pytest

from app.agent.classify import classify_ticket
from app.config import get_settings
from app.models.db import TicketCategory

pytestmark = pytest.mark.llm


@pytest.mark.asyncio
async def test_classify_returns_valid_fields():
    result = await classify_ticket(
        "Password reset help",
        "I forgot my CloudNova password and need to reset it.",
    )

    assert result.category in {
        TicketCategory.billing,
        TicketCategory.login,
        TicketCategory.api,
        TicketCategory.general,
    }
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.reasoning, str) and result.reasoning.strip()
    assert isinstance(result.chunks, list)


@pytest.mark.asyncio
async def test_confidence_always_between_zero_and_one():
    result = await classify_ticket(
        "API rate limit",
        "I am getting HTTP 429 from the CloudNova API. What are the limits?",
    )
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_clear_login_ticket_high_confidence():
    settings = get_settings()
    result = await classify_ticket(
        "I cannot log in",
        (
            "I cannot log in to CloudNova. 2FA is not working after I got a "
            "new phone. How do I reset my two-factor authentication?"
        ),
    )

    assert result.category == TicketCategory.login
    assert result.confidence >= settings.confidence_threshold, (
        f"expected confidence >= {settings.confidence_threshold}, "
        f"got {result.confidence}: {result.reasoning}"
    )


@pytest.mark.asyncio
async def test_vague_ticket_low_confidence():
    settings = get_settings()
    result = await classify_ticket(
        "Help",
        "it's broken",
    )

    assert 0.0 <= result.confidence <= 1.0
    assert result.confidence < settings.confidence_threshold, (
        f"expected confidence < {settings.confidence_threshold} for vague "
        f"ticket, got {result.confidence}: {result.reasoning}"
    )
