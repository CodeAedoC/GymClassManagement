from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Booking, BookingStatus, Slot, Member
from app.schemas.schemas import (
    BookingCreate,
    BookingResponse,
    BookingCancelResponse,
    BookingCompleteResponse,
    SlotResponse,
)
from app.services.booking_service import create_booking
from app.services.cancellation_service import cancel_booking
from app.services.streak_service import complete_booking

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def api_create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    return create_booking(db, payload.member_id, payload.slot_id)


@router.get("", response_model=List[BookingResponse])
def api_get_bookings(
    member_id: Optional[int] = Query(None),
    status: Optional[BookingStatus] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)
    if member_id is not None:
        query = query.filter(Booking.member_id == member_id)
    if status is not None:
        query = query.filter(Booking.status == status)
    return query.order_by(Booking.id.desc()).all()


@router.delete("/{id}", response_model=BookingCancelResponse)
def api_cancel_booking(id: int, db: Session = Depends(get_db)):
    return cancel_booking(db, id)


@router.post("/{id}/complete", response_model=BookingCompleteResponse)
def api_complete_booking(id: int, db: Session = Depends(get_db)):
    return complete_booking(db, id)
