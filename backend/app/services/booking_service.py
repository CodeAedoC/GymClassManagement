from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import (
    Member,
    Slot,
    Booking,
    BookingStatus,
    RestrictionStatus,
)
from app.core.metrics import GYM_BOOKINGS_TOTAL


def get_utc_now():
    return datetime.now(timezone.utc)


def create_booking(db: Session, member_id: int, slot_id: int) -> Booking:
    # 1. Fetch Member & Validate Active
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if not member.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Member account is inactive")

    # 2. Fetch Slot & Validate Exists
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    now = get_utc_now()

    # 3. Restriction Status Check
    # Handle timezone awareness for SQLite/PostgreSQL
    restr_until = member.restriction_until
    if restr_until and restr_until.tzinfo is None:
        restr_until = restr_until.replace(tzinfo=timezone.utc)

    slot_start = slot.start_time
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)

    if member.restriction_status == RestrictionStatus.FROZEN:
        if restr_until and restr_until > now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account frozen: booking not allowed")

    if member.restriction_status == RestrictionStatus.SAME_DAY_ONLY:
        if restr_until and restr_until > now:
            # Block booking if class starts > 2 hours from now
            if (slot_start - now) > timedelta(hours=2):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Same-day restriction active: cannot book classes starting more than 2 hours in advance"
                )

    # 4. Check Duplicate & Overlapping Bookings
    existing_same = (
        db.query(Booking)
        .filter(
            Booking.member_id == member_id,
            Booking.slot_id == slot_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
        )
        .first()
    )
    if existing_same:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member is already booked for this slot")

    # Check for any overlapping confirmed class booking
    slot_end = slot.end_time
    if slot_end.tzinfo is None:
        slot_end = slot_end.replace(tzinfo=timezone.utc)

    overlap_booking = (
        db.query(Booking)
        .join(Slot, Booking.slot_id == Slot.id)
        .filter(
            Booking.member_id == member_id,
            Booking.status == BookingStatus.CONFIRMED,
            Slot.start_time < slot_end,
            Slot.end_time > slot_start,
        )
        .first()
    )
    if overlap_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot book class: you already have an active reservation overlapping with this time slot."
        )

    # 5. Check Capacity
    confirmed_count = (
        db.query(Booking)
        .filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED)
        .count()
    )
    if confirmed_count >= slot.capacity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot fully booked")

    # 6. Create Booking
    booking = Booking(
        member_id=member_id,
        slot_id=slot_id,
        status=BookingStatus.CONFIRMED,
        penalty_applied=False,
        created_at=now,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    try:
        GYM_BOOKINGS_TOTAL.labels(status="CONFIRMED").inc()
    except Exception:
        pass

    return booking
