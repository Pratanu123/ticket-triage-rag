from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.db import TicketCategory, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10_000)


class RetrievedChunkOut(BaseModel):
    content: str
    source: str
    category: str
    chunk_index: int
    score: float


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    body: str
    category: TicketCategory
    confidence: float
    status: TicketStatus
    suggested_response: str | None
    reasoning: str | None
    retrieved_chunks: list[RetrievedChunkOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int


class TicketSearchHit(BaseModel):
    ticket_id: str
    subject: str | None = None
    body: str | None = None
    category: str | None = None
    confidence: float | None = None
    status: str | None = None
    reasoning: str | None = None
    suggested_response: str | None = None
    event: str | None = None
    timestamp: str | None = None
    score: float | None = None


class TicketSearchResponse(BaseModel):
    query: str
    total: int
    hits: list[TicketSearchHit]


class TicketOverrideRequest(BaseModel):
    """Human-in-the-loop: approve or edit a draft response for an escalated ticket."""

    suggested_response: str = Field(..., min_length=1, max_length=20_000)
    category: TicketCategory | None = Field(
        default=None,
        description="Optionally correct the category while resolving",
    )
    note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional reviewer note appended to reasoning",
    )


class HealthResponse(BaseModel):
    status: str
    postgres: str
    chromadb: str
    ollama: str
    knowledge_base_docs: int
