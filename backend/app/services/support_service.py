from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import Member, SupportTicket, TicketStatus, RestrictionStatus


def resolve_ticket(db: Session, ticket_id: int, action: str):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")

    member = db.query(Member).filter(Member.id == ticket.member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if action.upper() == "APPROVE":
        ticket.status = TicketStatus.RESOLVED
        # Reset member penalty points and lift active restrictions
        member.penalty_points = 0
        member.restriction_status = RestrictionStatus.NONE
        member.restriction_until = None
    else:
        ticket.status = TicketStatus.REJECTED

    db.commit()
    db.refresh(ticket)
    db.refresh(member)

    return {
        "status": ticket.status.value,
        "member_id": member.id,
        "penalty_points": member.penalty_points,
        "restriction_status": member.restriction_status,
    }
