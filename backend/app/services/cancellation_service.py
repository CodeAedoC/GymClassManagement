from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import (
    Member,
    Booking,
    Slot,
    BookingStatus,
    RestrictionStatus,
)
from app.core.metrics import GYM_LATE_CANCELLATIONS_TOTAL


def get_utc_now():
    return datetime.now(timezone.utc)


def cancel_booking(db: Session, booking_id: int):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel booking with status '{booking.status}'"
        )

    slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()
    member = db.query(Member).filter(Member.id == booking.member_id).first()

    now = get_utc_now()
    slot_start = slot.start_time
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)

    # Time delta check
    time_delta = slot_start - now
    late_threshold = timedelta(hours=2)

    is_late = time_delta < late_threshold
    booking.status = BookingStatus.CANCELLED
    warning_msg = None

    if is_late:
        booking.penalty_applied = True
        member.penalty_points += 1
        warning_msg = "Late cancellation penalty applied (+1 point)"
        try:
            GYM_LATE_CANCELLATIONS_TOTAL.inc()
        except Exception:
            pass

        # Apply Escalation Tiers
        apply_penalty_escalation(member, now)
    else:
        booking.penalty_applied = False

    db.commit()
    db.refresh(member)
    db.refresh(booking)

    return {
        "message": "Booking cancelled",
        "penalty_applied": booking.penalty_applied,
        "penalty_points": member.penalty_points,
        "warning": warning_msg,
    }


def record_no_show(db: Session, booking_id: int):
    """Mark a booking as NO_SHOW and apply +1 penalty point and escalation tier."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    booking.status = BookingStatus.NO_SHOW
    booking.penalty_applied = True

    member = db.query(Member).filter(Member.id == booking.member_id).first()
    member.penalty_points += 1

    now = get_utc_now()
    apply_penalty_escalation(member, now)

    db.commit()
    db.refresh(member)
    db.refresh(booking)
    return booking


def apply_penalty_escalation(member: Member, now: datetime):
    """
    Tier 1 (0 to 2 Penalty Points): restriction_status = NONE
    Tier 2 (3 Penalty Points): restriction_status = SAME_DAY_ONLY, restriction_until = NOW + 7 DAYS
    Tier 3 (Offense while restricted): restriction_until = NOW + 14 DAYS
    Tier 4 (Further offenses): restriction_status = FROZEN, restriction_until = NOW + 7 DAYS
    """
    # Check if currently active restricted
    is_currently_restricted = False
    restr_until = member.restriction_until
    if restr_until:
        if restr_until.tzinfo is None:
            restr_until = restr_until.replace(tzinfo=timezone.utc)
        if restr_until > now and member.restriction_status in [RestrictionStatus.SAME_DAY_ONLY, RestrictionStatus.FROZEN]:
            is_currently_restricted = True

    if is_currently_restricted:
        # Offense while restricted
        if member.penalty_points >= 5:
            # Tier 4: Further offenses -> FROZEN for 7 days
            member.restriction_status = RestrictionStatus.FROZEN
            member.restriction_until = (now + timedelta(days=7)).replace(tzinfo=None)
        else:
            # Tier 3: Offense while restricted -> Extend to NOW + 14 days
            member.restriction_until = (now + timedelta(days=14)).replace(tzinfo=None)
    else:
        # Not previously actively restricted
        if member.penalty_points >= 3:
            # Tier 2: 3 Penalty Points -> SAME_DAY_ONLY for 7 days
            member.restriction_status = RestrictionStatus.SAME_DAY_ONLY
            member.restriction_until = (now + timedelta(days=7)).replace(tzinfo=None)
        else:
            # Tier 1: 0 to 2 points
            member.restriction_status = RestrictionStatus.NONE
            member.restriction_until = None
