from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Member, StreakProfile
from app.schemas.schemas import MemberCreate, MemberResponse

router = APIRouter(prefix="/members", tags=["Members"])


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def api_create_member(payload: MemberCreate, db: Session = Depends(get_db)):
    existing = db.query(Member).filter(Member.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member email already exists")

    member = Member(
        name=payload.name,
        email=payload.email,
        membership_type=payload.membership_type,
    )
    db.add(member)
    db.flush()

    # Automatically initialize streak profile
    profile = StreakProfile(
        member_id=member.id,
        weekly_target_days=3,
        current_streak_weeks=0,
        attended_this_week=0,
        lives_remaining=3,
        lives_earned_this_week=0,
    )
    db.add(profile)
    db.commit()
    db.refresh(member)
    return member


@router.get("", response_model=List[MemberResponse])
def api_list_members(db: Session = Depends(get_db)):
    return db.query(Member).order_by(Member.id.asc()).all()


@router.get("/{id}", response_model=MemberResponse)
def api_get_member(id: int, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return member
