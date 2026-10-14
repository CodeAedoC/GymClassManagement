from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.models import Slot, Booking, BookingStatus
from app.schemas.schemas import SlotCreate, SlotResponse

router = APIRouter(prefix="/slots", tags=["Slots"])


@router.post("", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
def api_create_slot(payload: SlotCreate, db: Session = Depends(get_db)):
    slot = Slot(
        title=payload.title,
        capacity=payload.capacity,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    slot.booked_count = 0
    return slot


@router.get("", response_model=List[SlotResponse])
def api_get_slots(db: Session = Depends(get_db)):
    slots = db.query(Slot).order_by(Slot.start_time.asc()).all()
    results = []
    for s in slots:
        count = (
            db.query(Booking)
            .filter(Booking.slot_id == s.id, Booking.status == BookingStatus.CONFIRMED)
            .count()
        )
        s_dict = {
            "id": s.id,
            "title": s.title,
            "capacity": s.capacity,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "booked_count": count,
        }
        results.append(s_dict)
    return results
