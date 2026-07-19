"""Classify a support ticket using RAG context + local Ollama."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_chat_model
from app.config import Settings, get_settings
from app.metrics import observe_classify_duration
from app.models.db import TicketCategory
from app.rag.retrieve import RetrievedChunk, format_context, retrieve

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    TicketCategory.billing.value,
    TicketCategory.login.value,
    TicketCategory.api.value,
    TicketCategory.general.value,
}

CLASSIFY_SYSTEM = """You are a support ticket classifier for CloudNova, a SaaS product.

Given a support ticket and retrieved knowledge-base excerpts, classify the ticket.

You MUST return a single JSON object with exactly these keys:
{
  "category": "billing" | "login" | "api" | "general",
  "confidence": <number between 0.0 and 1.0>,
  "reasoning": "<2-4 sentence explanation>"
}

Rules:
- category MUST be one of: billing, login, api, general
- confidence reflects how certain you are that (a) the category is correct AND
  (b) the retrieved knowledge base can answer the ticket
- Prefer lower confidence when the ticket is ambiguous, out of scope, or the
  retrieved context is weak / unrelated
- Do not invent product facts
- Return JSON only — no markdown fences, no extra text
"""


@dataclass
class ClassificationResult:
    category: TicketCategory
    confidence: float
    reasoning: str
    chunks: list[RetrievedChunk] = field(default_factory=list)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
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


def _parse_classification(payload: dict) -> tuple[TicketCategory, float, str]:
    raw_cat = str(payload.get("category", "")).strip().lower()
    if raw_cat not in VALID_CATEGORIES:
        raise ValueError(f"invalid category: {raw_cat!r}")

    try:
        confidence = float(payload.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be a number") from exc
    confidence = max(0.0, min(1.0, confidence))

    reasoning = str(payload.get("reasoning") or "").strip()
    if not reasoning:
        raise ValueError("reasoning is required")

    return TicketCategory(raw_cat), confidence, reasoning


async def _invoke_classifier(
    subject: str,
    body: str,
    context_block: str,
    *,
    settings: Settings,
    retry_hint: str | None = None,
) -> str:
    user_prompt = f"""TICKET SUBJECT:
{subject}

TICKET BODY:
{body}

RETRIEVED KNOWLEDGE BASE CONTEXT:
{context_block or "(no relevant documents retrieved)"}
"""
    if retry_hint:
        user_prompt += (
            f"\nPREVIOUS OUTPUT WAS INVALID: {retry_hint}\n"
            "Return valid JSON only, matching the required schema.\n"
        )
    user_prompt += "\nRespond with JSON only."

    llm = get_chat_model(settings, json_mode=True)
    response = await llm.ainvoke(
        [SystemMessage(content=CLASSIFY_SYSTEM), HumanMessage(content=user_prompt)]
    )
    return response.content if isinstance(response.content, str) else str(response.content)


async def classify_ticket(
    subject: str,
    body: str,
    *,
    settings: Settings | None = None,
) -> ClassificationResult:
    """
    Retrieve KB chunks and classify the ticket.

    Retries the LLM once if the first response fails JSON/schema validation.
    """
    settings = settings or get_settings()
    started = time.perf_counter()
    query = f"{subject}\n\n{body}"
    chunks = retrieve(query, settings=settings)
    context_block = format_context(chunks)

    last_error: str | None = None
    try:
        for attempt in range(2):
            raw = await _invoke_classifier(
                subject,
                body,
                context_block,
                settings=settings,
                retry_hint=last_error if attempt == 1 else None,
            )
            try:
                payload = _extract_json(raw)
                category, confidence, reasoning = _parse_classification(payload)
                return ClassificationResult(
                    category=category,
                    confidence=confidence,
                    reasoning=reasoning,
                    chunks=chunks,
                )
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                last_error = str(exc)
                logger.warning(
                    "Classification parse failed (attempt %s): %s | raw=%r",
                    attempt + 1,
                    exc,
                    raw[:500],
                )

        return ClassificationResult(
            category=TicketCategory.general,
            confidence=0.0,
            reasoning=(
                "Classifier returned unparseable output after retry; "
                f"escalating for human review. Last error: {last_error}"
            ),
            chunks=chunks,
        )
    finally:
        observe_classify_duration(time.perf_counter() - started)
