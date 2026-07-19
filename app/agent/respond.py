"""Draft a customer response or escalate based on classification confidence."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.classify import ClassificationResult
from app.agent.llm import get_chat_model
from app.config import Settings, get_settings
from app.models.db import TicketStatus
from app.rag.retrieve import format_context

logger = logging.getLogger(__name__)

RESPOND_SYSTEM = """You are a CloudNova support agent drafting a reply to a customer.

Rules:
- Ground every factual claim in the retrieved knowledge-base context below
- Be concise, friendly, and actionable
- Explicitly cite the source document filename(s) you used, e.g.
  "According to login-2fa.md, …"
- If the context is insufficient, say so briefly instead of inventing details
- Return plain text only (the customer-facing reply). No JSON. No markdown fences.
"""


@dataclass
class ResponseResult:
    status: TicketStatus
    suggested_response: str | None
    cited_sources: list[str]


def _cited_sources(classification: ClassificationResult) -> list[str]:
    seen: list[str] = []
    for chunk in classification.chunks:
        if chunk.source not in seen:
            seen.append(chunk.source)
    return seen


async def draft_or_escalate(
    subject: str,
    body: str,
    classification: ClassificationResult,
    *,
    settings: Settings | None = None,
) -> ResponseResult:
    """
    If confidence >= threshold, draft a reply citing retrieved docs.
    Otherwise skip drafting and mark needs_human_review.
    """
    settings = settings or get_settings()
    sources = _cited_sources(classification)

    if classification.confidence < settings.confidence_threshold:
        logger.info(
            "Escalating ticket (confidence=%.3f < threshold=%.3f)",
            classification.confidence,
            settings.confidence_threshold,
        )
        return ResponseResult(
            status=TicketStatus.needs_human_review,
            suggested_response=None,
            cited_sources=sources,
        )

    context_block = format_context(classification.chunks)
    user_prompt = f"""TICKET SUBJECT:
{subject}

TICKET BODY:
{body}

CATEGORY: {classification.category.value}
CLASSIFIER REASONING: {classification.reasoning}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context_block or "(no relevant documents retrieved)"}

Write the customer-facing reply now. Cite source filenames from the context."""

    llm = get_chat_model(settings, json_mode=False)
    response = await llm.ainvoke(
        [SystemMessage(content=RESPOND_SYSTEM), HumanMessage(content=user_prompt)]
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    draft = text.strip() or None

    if not draft:
        return ResponseResult(
            status=TicketStatus.needs_human_review,
            suggested_response=None,
            cited_sources=sources,
        )

    return ResponseResult(
        status=TicketStatus.auto_resolved,
        suggested_response=draft,
        cited_sources=sources,
    )
