import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class MembershipType(str, enum.Enum):
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"


class RestrictionStatus(str, enum.Enum):
    NONE = "NONE"
    SAME_DAY_ONLY = "SAME_DAY_ONLY"
    FROZEN = "FROZEN"


class AchievementType(str, enum.Enum):
    OVER_ACHIEVER_1_WEEK = "OVER_ACHIEVER_1_WEEK"
    OVER_ACHIEVER_2_WEEKS = "OVER_ACHIEVER_2_WEEKS"
    STREAK_MILESTONE_4_WEEKS = "STREAK_MILESTONE_4_WEEKS"
    ATTENDED_5_PLUS_CLASSES = "ATTENDED_5_PLUS_CLASSES"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    membership_type = Column(SQLEnum(MembershipType), default=MembershipType.BASIC, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    penalty_points = Column(Integer, default=0, nullable=False)
    restriction_status = Column(SQLEnum(RestrictionStatus), default=RestrictionStatus.NONE, nullable=False)
    restriction_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    streak_profile = relationship("StreakProfile", back_populates="member", uselist=False, cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="member", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="member", cascade="all, delete-orphan")
    tickets = relationship("SupportTicket", back_populates="member", cascade="all, delete-orphan")


class StreakProfile(Base):
    __tablename__ = "streak_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), unique=True, nullable=False)
    weekly_target_days = Column(Integer, default=3, nullable=False)
    current_streak_weeks = Column(Integer, default=0, nullable=False)
    attended_this_week = Column(Integer, default=0, nullable=False)
    lives_remaining = Column(Integer, default=3, nullable=False)
    lives_earned_this_week = Column(Integer, default=0, nullable=False)
    last_week_processed = Column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("weekly_target_days >= 1 AND weekly_target_days <= 7", name="check_weekly_target_range"),
        CheckConstraint("lives_remaining >= 0 AND lives_remaining <= 3", name="check_lives_remaining_range"),
        CheckConstraint("lives_earned_this_week >= 0 AND lives_earned_this_week <= 1", name="check_lives_earned_range"),
    )

    member = relationship("Member", back_populates="streak_profile")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    achievement_type = Column(SQLEnum(AchievementType), nullable=False)
    lives_awarded = Column(Integer, default=1, nullable=False)
    earned_at = Column(DateTime, default=utcnow, nullable=False)

    member = relationship("Member", back_populates="achievements")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    start_time = Column(DateTime, index=True, nullable=False)
    end_time = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="check_slot_capacity_positive"),
    )

    bookings = relationship("Booking", back_populates="slot", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.CONFIRMED, nullable=False)
    penalty_applied = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    member = relationship("Member", back_populates="bookings")
    slot = relationship("Slot", back_populates="bookings")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    member = relationship("Member", back_populates="tickets")
