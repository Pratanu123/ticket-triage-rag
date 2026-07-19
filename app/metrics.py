"""Prometheus metrics for triage outcomes and LLM timings."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

LLM_CLASSIFY_DURATION = Histogram(
    "llm_classify_duration_seconds",
    "Time spent in LLM classification (including retries)",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0),
)

LLM_RESPOND_DURATION = Histogram(
    "llm_respond_duration_seconds",
    "Time spent in LLM response drafting",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0),
)

TICKET_OUTCOMES = Counter(
    "ticket_triage_outcomes_total",
    "Ticket triage outcomes by status",
    labelnames=("status",),
)


def observe_classify_duration(seconds: float) -> None:
    LLM_CLASSIFY_DURATION.observe(seconds)


def observe_respond_duration(seconds: float) -> None:
    LLM_RESPOND_DURATION.observe(seconds)


def record_ticket_outcome(status: str) -> None:
    TICKET_OUTCOMES.labels(status=status).inc()
