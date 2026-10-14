from fastapi import APIRouter
from app.api.v1.endpoints import (
    bookings,
    streak,
    support,
    analytics,
    slots,
    members,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(members.router)
api_router.include_router(slots.router)
api_router.include_router(bookings.router)
api_router.include_router(streak.router)
api_router.include_router(support.router)
api_router.include_router(analytics.router)
