from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import StreakProfile
from app.services.streak_service import evaluate_member_week
from app.services.analytics_service import reset_monthly_penalty_points

celery_app = Celery("gym_tasks", broker=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    # Weekly evaluation routine: Every Sunday at 23:59 UTC
    "sunday-weekly-streak-evaluation": {
        "task": "app.tasks.evaluate_all_streaks_task",
        "schedule": crontab(hour=23, minute=59, day_of_week="sunday"),
    },
    # Monthly penalty reset: 1st day of every month at 00:00 UTC
    "monthly-penalty-points-reset": {
        "task": "app.tasks.monthly_penalty_reset_task",
        "schedule": crontab(hour=0, minute=0, day_of_month="1"),
    },
}
celery_app.conf.timezone = "UTC"


@celery_app.task
def evaluate_all_streaks_task():
    db = SessionLocal()
    try:
        profiles = db.query(StreakProfile).all()
        for profile in profiles:
            evaluate_member_week(db, profile)
        return f"Evaluated {len(profiles)} member streaks successfully."
    finally:
        db.close()


@celery_app.task
def monthly_penalty_reset_task():
    db = SessionLocal()
    try:
        reset_monthly_penalty_points(db)
        return "Reset penalty points for all members."
    finally:
        db.close()
