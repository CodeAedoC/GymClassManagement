from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import Member, Booking, Slot, StreakProfile, RestrictionStatus, BookingStatus


def reset_monthly_penalty_points(db: Session):
    """
    Monthly Reset: On the 1st day of every month at 00:00 UTC,
    all members' penalty_points reset to 0.
    (Active time-based restrictions remain until restriction_until expires).
    """
    members = db.query(Member).all()
    for member in members:
        member.penalty_points = 0
    db.commit()


def get_occupancy_analytics(db: Session):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    total_active_members = db.query(Member).filter(Member.is_active == True).count()
    
    # SQLite/PostgreSQL compliant date filtering
    today_bookings = (
        db.query(Booking)
        .filter(Booking.created_at >= today_start, Booking.created_at <= today_end)
        .count()
    )

    total_slots_cap = db.query(func.sum(Slot.capacity)).scalar() or 0
    total_confirmed = db.query(Booking).filter(Booking.status == BookingStatus.CONFIRMED).count()
    slot_utilization_pct = 0.0
    if total_slots_cap > 0:
        slot_utilization_pct = round((total_confirmed / total_slots_cap) * 100, 1)

    restricted_members_count = (
        db.query(Member)
        .filter(
            Member.restriction_status.in_([RestrictionStatus.SAME_DAY_ONLY, RestrictionStatus.FROZEN]),
            Member.restriction_until > now,
        )
        .count()
    )

    avg_streak = db.query(func.avg(StreakProfile.current_streak_weeks)).scalar() or 0.0

    return {
        "total_active_members": total_active_members,
        "today_bookings": today_bookings,
        "slot_utilization_pct": float(slot_utilization_pct),
        "restricted_members_count": restricted_members_count,
        "average_community_streak_weeks": round(float(avg_streak), 1),
    }
