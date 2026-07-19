from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.db import TicketCategory, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10_000)


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
    retrieved_context: str | None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int


class HealthResponse(BaseModel):
    status: str
    postgres: str
    chromadb: str
    knowledge_base_docs: int
