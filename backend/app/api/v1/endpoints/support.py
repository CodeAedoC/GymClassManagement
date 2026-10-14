from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import SupportTicket
from app.schemas.schemas import TicketCreate, TicketResponse, TicketResolveRequest, TicketResolveResponse
from app.services.support_service import resolve_ticket

router = APIRouter(prefix="/support", tags=["Support"])


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def api_create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    ticket = SupportTicket(member_id=payload.member_id, reason=payload.reason)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets", response_model=List[TicketResponse])
def api_list_tickets(db: Session = Depends(get_db)):
    return db.query(SupportTicket).order_by(SupportTicket.id.desc()).all()


@router.post("/tickets/{id}/resolve", response_model=TicketResolveResponse)
def api_resolve_ticket(id: int, payload: TicketResolveRequest, db: Session = Depends(get_db)):
    return resolve_ticket(db, id, payload.action)
