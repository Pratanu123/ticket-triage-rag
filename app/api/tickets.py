from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.classify import classify_ticket
from app.agent.respond import draft_or_escalate
from app.database import get_db
from app.models.db import Ticket, TicketStatus
from app.models.schemas import (
    RetrievedChunkOut,
    TicketCreate,
    TicketListResponse,
    TicketOverrideRequest,
    TicketResponse,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ticket_to_response(ticket: Ticket) -> TicketResponse:
    raw_chunks = ticket.retrieved_chunks or []
    chunks = [RetrievedChunkOut.model_validate(c) for c in raw_chunks]
    return TicketResponse(
        id=ticket.id,
        subject=ticket.subject,
        body=ticket.body,
        category=ticket.category,
        confidence=ticket.confidence,
        status=ticket.status,
        suggested_response=ticket.suggested_response,
        reasoning=ticket.reasoning,
        retrieved_chunks=chunks,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    classification = await classify_ticket(payload.subject, payload.body)
    response = await draft_or_escalate(
        payload.subject, payload.body, classification
    )

    ticket = Ticket(
        subject=payload.subject,
        body=payload.body,
        category=classification.category,
        confidence=classification.confidence,
        status=response.status,
        suggested_response=response.suggested_response,
        reasoning=classification.reasoning,
        retrieved_chunks=[c.to_dict() for c in classification.chunks],
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return _ticket_to_response(ticket)


@router.get("", response_model=TicketListResponse)
async def list_tickets(db: AsyncSession = Depends(get_db)) -> TicketListResponse:
    total = await db.scalar(select(func.count()).select_from(Ticket)) or 0
    rows = (
        await db.scalars(select(Ticket).order_by(Ticket.created_at.desc()))
    ).all()
    return TicketListResponse(
        tickets=[_ticket_to_response(t) for t in rows],
        total=int(total),
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_to_response(ticket)


@router.post("/{ticket_id}/override", response_model=TicketResponse)
async def override_ticket(
    ticket_id: UUID,
    payload: TicketOverrideRequest,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """
    Human-in-the-loop: approve or edit a response for a low-confidence ticket.

    Sets status to `human_resolved` and stores the reviewer-provided reply.
    """
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.suggested_response = payload.suggested_response.strip()
    ticket.status = TicketStatus.human_resolved
    if payload.category is not None:
        ticket.category = payload.category
    if payload.note:
        note = payload.note.strip()
        existing = ticket.reasoning or ""
        ticket.reasoning = (
            f"{existing}\n\n[human override] {note}".strip()
            if existing
            else f"[human override] {note}"
        )

    await db.commit()
    await db.refresh(ticket)
    return _ticket_to_response(ticket)
