from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import StreakTargetUpdate, StreakStatusResponse
from app.services.streak_service import set_streak_target, get_streak_status

router = APIRouter(prefix="/streak", tags=["Streak"])


@router.post("/target")
def api_set_streak_target(payload: StreakTargetUpdate, db: Session = Depends(get_db)):
    return set_streak_target(db, payload.member_id, payload.weekly_target_days)


@router.get("/status", response_model=StreakStatusResponse)
def api_get_streak_status(member_id: int = Query(...), db: Session = Depends(get_db)):
    return get_streak_status(db, member_id)
