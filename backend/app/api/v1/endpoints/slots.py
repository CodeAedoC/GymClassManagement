from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
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


from datetime import datetime, timezone, timedelta

@router.get("", response_model=List[SlotResponse])
def api_get_slots(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    slots = db.query(Slot).order_by(Slot.start_time.asc()).all()

    # If slots are in the past or empty, automatically generate fresh upcoming slots
    if not slots or any((s.start_time.replace(tzinfo=timezone.utc) if s.start_time.tzinfo is None else s.start_time) < now for s in slots):
        sample_slots = [
            ("HIIT & Core (Starts in 1h - Late Cancel Demo)", 10, timedelta(minutes=60), timedelta(minutes=120)),
            ("Yoga & Mobility (Starts in 3h - Clean Cancel Demo)", 8, timedelta(hours=3), timedelta(hours=4)),
            ("Pilates Flow (Starts in 3.5h - Overlap Conflict Demo)", 6, timedelta(hours=3, minutes=30), timedelta(hours=4, minutes=30)),
            ("Spin & Sprint (Starts in 5h - Clean Cancel Demo)", 12, timedelta(hours=5), timedelta(hours=6)),
            ("CrossFit Open Gym (Tomorrow)", 6, timedelta(hours=24), timedelta(hours=25)),
        ]
        
        # Reset and populate clean slots
        db.query(Slot).delete()
        db.commit()

        for title, cap, start_off, end_off in sample_slots:
            new_s = Slot(
                title=title,
                capacity=cap,
                start_time=(now + start_off).replace(tzinfo=None),
                end_time=(now + end_off).replace(tzinfo=None)
            )
            db.add(new_s)
        db.commit()
        slots = db.query(Slot).order_by(Slot.start_time.asc()).all()

    results = []
    for s in slots:
        count = (
            db.query(Booking)
            .filter(Booking.slot_id == s.id, Booking.status == BookingStatus.CONFIRMED)
            .count()
        )
        st = s.start_time.replace(tzinfo=timezone.utc) if s.start_time.tzinfo is None else s.start_time
        et = s.end_time.replace(tzinfo=timezone.utc) if s.end_time.tzinfo is None else s.end_time
        s_dict = {
            "id": s.id,
            "title": s.title,
            "capacity": s.capacity,
            "start_time": st.isoformat(),
            "end_time": et.isoformat(),
            "booked_count": count,
        }
        results.append(s_dict)
    return results
