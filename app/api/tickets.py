from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.triage import triage_ticket
from app.database import get_db
from app.models.db import Ticket
from app.models.schemas import TicketCreate, TicketListResponse, TicketResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
) -> Ticket:
    result = await triage_ticket(payload.subject, payload.body)

    ticket = Ticket(
        subject=payload.subject,
        body=payload.body,
        category=result.category,
        confidence=result.confidence,
        status=result.status,
        suggested_response=result.suggested_response,
        reasoning=result.reasoning,
        retrieved_context=result.retrieved_context or None,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("", response_model=TicketListResponse)
async def list_tickets(db: AsyncSession = Depends(get_db)) -> TicketListResponse:
    total = await db.scalar(select(func.count()).select_from(Ticket)) or 0
    rows = (
        await db.scalars(select(Ticket).order_by(Ticket.created_at.desc()))
    ).all()
    return TicketListResponse(
        tickets=[TicketResponse.model_validate(t) for t in rows],
        total=int(total),
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
