"""Classification + response generation with confidence-based escalation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import Settings, get_settings
from app.models.db import TicketCategory, TicketStatus
from app.rag.retrieve import format_context, retrieve as retrieve_context

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {c.value for c in TicketCategory}

CLASSIFY_SYSTEM = """You are a support ticket triage assistant for CloudNova, a fictional SaaS
product for project tracking and team collaboration.

Given a support ticket and retrieved knowledge-base excerpts, you must:
1. Classify the ticket into exactly one category:
   billing | login | api | refunds | account | general | unknown
2. Provide a confidence score between 0.0 and 1.0 reflecting how certain you are
   that the category is correct AND that the knowledge base can answer the ticket.
3. Explain your reasoning briefly (2–4 sentences).
4. If confidence is high enough to auto-resolve, draft a helpful customer-facing
   response grounded ONLY in the retrieved context. If the context is insufficient,
   lower confidence and leave suggested_response empty.

Rules:
- Prefer lower confidence over inventing product facts not present in the context.
- Use "unknown" when the ticket is out of scope or ambiguous.
- Return STRICT JSON with keys:
  category, confidence, reasoning, suggested_response
- suggested_response must be a string (empty string when not drafting a reply).
- Do not wrap the JSON in markdown code fences.
"""


@dataclass
class TriageResult:
    category: TicketCategory
    confidence: float
    status: TicketStatus
    suggested_response: str | None
    reasoning: str
    retrieved_context: str | None


def get_chat_model(settings: Settings | None = None) -> ChatOllama:
    """Local Ollama chat model (llama3.1:8b by default)."""
    settings = settings or get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        format="json",
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    # Strip optional markdown fences some models still emit
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _parse_category(raw: str) -> TicketCategory:
    value = (raw or "unknown").strip().lower()
    if value not in VALID_CATEGORIES:
        return TicketCategory.unknown
    return TicketCategory(value)


def _clamp_confidence(raw: object) -> float:
    try:
        score = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


async def triage_ticket(
    subject: str,
    body: str,
    *,
    settings: Settings | None = None,
) -> TriageResult:
    settings = settings or get_settings()
    query = f"{subject}\n\n{body}"
    chunks = retrieve_context(query, settings=settings)
    context_block = format_context(chunks)

    user_prompt = f"""TICKET SUBJECT:
{subject}

TICKET BODY:
{body}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context_block or "(no relevant documents retrieved)"}

Respond with JSON only."""

    llm = get_chat_model(settings)
    response = await llm.ainvoke(
        [SystemMessage(content=CLASSIFY_SYSTEM), HumanMessage(content=user_prompt)]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)

    try:
        payload = _extract_json(content)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.exception("Failed to parse LLM triage JSON")
        return TriageResult(
            category=TicketCategory.unknown,
            confidence=0.0,
            status=TicketStatus.needs_human_review,
            suggested_response=None,
            reasoning=f"Model returned unparseable output; escalating. Error: {exc}",
            retrieved_context=context_block or None,
        )

    category = _parse_category(str(payload.get("category", "unknown")))
    confidence = _clamp_confidence(payload.get("confidence", 0.0))
    reasoning = str(payload.get("reasoning") or "").strip() or "No reasoning provided."
    suggested = str(payload.get("suggested_response") or "").strip() or None

    if confidence >= settings.confidence_threshold and suggested:
        status = TicketStatus.auto_resolved
    else:
        status = TicketStatus.needs_human_review
        if confidence < settings.confidence_threshold:
            suggested = None

    return TriageResult(
        category=category,
        confidence=confidence,
        status=status,
        suggested_response=suggested,
        reasoning=reasoning,
        retrieved_context=context_block,
    )
