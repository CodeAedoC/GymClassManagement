from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import OccupancyAnalyticsResponse
from app.services.analytics_service import get_occupancy_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/occupancy", response_model=OccupancyAnalyticsResponse)
def api_get_occupancy_analytics(db: Session = Depends(get_db)):
    return get_occupancy_analytics(db)
