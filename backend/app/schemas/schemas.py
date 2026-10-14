from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.models import MembershipType, RestrictionStatus, BookingStatus, TicketStatus


# --- Member Schemas ---
class MemberBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    membership_type: MembershipType = MembershipType.BASIC


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    id: int
    is_active: bool
    penalty_points: int
    restriction_status: RestrictionStatus
    restriction_until: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Streak Schemas ---
class StreakTargetUpdate(BaseModel):
    member_id: int
    weekly_target_days: int = Field(..., ge=1, le=7)


class StreakStatusResponse(BaseModel):
    member_id: int
    weekly_target_days: int
    attended_this_week: int
    current_streak_weeks: int
    lives_remaining: int
    lives_earned_this_week: int
    achievements: List[str]


# --- Slot Schemas ---
class SlotBase(BaseModel):
    title: str = Field(..., max_length=100)
    capacity: int = Field(..., gt=0)
    start_time: datetime
    end_time: datetime


class SlotCreate(SlotBase):
    pass


class SlotResponse(SlotBase):
    id: int
    booked_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# --- Booking Schemas ---
class BookingCreate(BaseModel):
    member_id: int
    slot_id: int


class BookingResponse(BaseModel):
    id: int
    member_id: int
    slot_id: int
    status: BookingStatus
    penalty_applied: bool = False
    created_at: Optional[datetime] = None
    slot: Optional[SlotResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BookingCancelResponse(BaseModel):
    message: str
    penalty_applied: bool
    penalty_points: int
    warning: Optional[str] = None


class BookingCompleteResponse(BaseModel):
    message: str
    attended_this_week: int
    target_days: int


# --- Support Ticket Schemas ---
class TicketCreate(BaseModel):
    member_id: int
    reason: str


class TicketResolveRequest(BaseModel):
    action: str = Field(..., description="Action, e.g., 'APPROVE'")


class TicketResponse(BaseModel):
    id: int
    member_id: int
    reason: str
    status: TicketStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketResolveResponse(BaseModel):
    status: str
    member_id: int
    penalty_points: int
    restriction_status: RestrictionStatus


# --- Analytics Schemas ---
class OccupancyAnalyticsResponse(BaseModel):
    total_active_members: int
    today_bookings: int
    slot_utilization_pct: float
    restricted_members_count: int
    average_community_streak_weeks: float
