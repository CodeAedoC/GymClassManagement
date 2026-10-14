from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import (
    Member,
    StreakProfile,
    Achievement,
    Booking,
    BookingStatus,
    AchievementType,
)


def get_utc_now():
    return datetime.now(timezone.utc)


def complete_booking(db: Session, booking_id: int):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status == BookingStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is already completed")

    booking.status = BookingStatus.COMPLETED

    profile = db.query(StreakProfile).filter(StreakProfile.member_id == booking.member_id).first()
    if not profile:
        profile = StreakProfile(
            member_id=booking.member_id,
            weekly_target_days=3,
            current_streak_weeks=0,
            attended_this_week=0,
            lives_remaining=3,
            lives_earned_this_week=0,
        )
        db.add(profile)
        db.flush()

    profile.attended_this_week += 1
    db.commit()
    db.refresh(profile)

    return {
        "message": "Check-in successful",
        "attended_this_week": profile.attended_this_week,
        "target_days": profile.weekly_target_days,
    }


def set_streak_target(db: Session, member_id: int, weekly_target_days: int):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    profile = db.query(StreakProfile).filter(StreakProfile.member_id == member_id).first()
    if not profile:
        profile = StreakProfile(
            member_id=member_id,
            weekly_target_days=weekly_target_days,
            current_streak_weeks=0,
            attended_this_week=0,
            lives_remaining=3,
            lives_earned_this_week=0,
        )
        db.add(profile)
    else:
        profile.weekly_target_days = weekly_target_days

    db.commit()
    db.refresh(profile)

    return {
        "member_id": profile.member_id,
        "weekly_target_days": profile.weekly_target_days,
        "current_streak_weeks": profile.current_streak_weeks,
    }


def get_streak_status(db: Session, member_id: int):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    profile = db.query(StreakProfile).filter(StreakProfile.member_id == member_id).first()
    if not profile:
        profile = StreakProfile(
            member_id=member_id,
            weekly_target_days=3,
            current_streak_weeks=0,
            attended_this_week=0,
            lives_remaining=3,
            lives_earned_this_week=0,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    achievements = db.query(Achievement).filter(Achievement.member_id == member_id).all()
    ach_names = [a.achievement_type.value for a in achievements]

    return {
        "member_id": profile.member_id,
        "weekly_target_days": profile.weekly_target_days,
        "attended_this_week": profile.attended_this_week,
        "current_streak_weeks": profile.current_streak_weeks,
        "lives_remaining": profile.lives_remaining,
        "lives_earned_this_week": profile.lives_earned_this_week,
        "achievements": ach_names,
    }


def evaluate_member_week(db: Session, profile: StreakProfile):
    """
    Weekly Evaluation Routine:
    - Success (attended_this_week >= weekly_target_days):
        current_streak_weeks += 1
        If achievement triggered (attended_this_week > weekly_target_days -> OVER_ACHIEVER_1_WEEK):
            award +1 life ONLY IF lives_earned_this_week < 1 AND lives_remaining < 3.
            lives_earned_this_week += 1
    - Deficit (attended_this_week < weekly_target_days):
        If lives_remaining > 0:
            lives_remaining -= 1 (streak maintained)
        If lives_remaining == 0:
            current_streak_weeks = 0
            lives_remaining = 3 (restore default)
    - Reset Weekly Counters:
        attended_this_week = 0
        lives_earned_this_week = 0
    """
    now = get_utc_now()
    if profile.attended_this_week >= profile.weekly_target_days:
        # Success
        profile.current_streak_weeks += 1

        # Check over-achievement
        if profile.attended_this_week > profile.weekly_target_days:
            award_achievement_and_life(db, profile, AchievementType.OVER_ACHIEVER_1_WEEK, now)
        elif profile.attended_this_week >= 5:
            award_achievement_and_life(db, profile, AchievementType.ATTENDED_5_PLUS_CLASSES, now)

        if profile.current_streak_weeks == 4:
            award_achievement_and_life(db, profile, AchievementType.STREAK_MILESTONE_4_WEEKS, now)
    else:
        # Deficit
        if profile.lives_remaining > 0:
            profile.lives_remaining -= 1
        else:
            profile.current_streak_weeks = 0
            profile.lives_remaining = 3

    # Reset weekly counters
    profile.attended_this_week = 0
    profile.lives_earned_this_week = 0
    profile.last_week_processed = now.date()
    db.commit()
    db.refresh(profile)


def award_achievement_and_life(
    db: Session,
    profile: StreakProfile,
    ach_type: AchievementType,
    now: datetime,
):
    # Record achievement
    ach = Achievement(
        member_id=profile.member_id,
        achievement_type=ach_type,
        lives_awarded=1,
        earned_at=now,
    )
    db.add(ach)

    # Award life only if under weekly limit (1/week) AND lives_remaining < 3
    if profile.lives_earned_this_week < 1:
        if profile.lives_remaining < 3:
            profile.lives_remaining += 1
        profile.lives_earned_this_week += 1
