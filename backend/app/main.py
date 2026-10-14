from fastapi import FastAPI, Depends, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import get_db, Base, engine
from app.api.v1.router import api_router

# Initialize tables conditionally if database is available
try:
    if "sqlite" in settings.DATABASE_URL or settings.ENVIRONMENT != "test":
        Base.metadata.create_all(bind=engine)
except Exception:
    # Allows offline import during test suite initialization
    pass

app = FastAPI(
    title=settings.APP_NAME,
    description="Gym & Fitness Facility Membership Portal REST API with Automated Streak Tracking and Penalty Enforcement",
    version="1.0.0",
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus instrumentator exposing /metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    """Liveness probe: verifies the FastAPI application process is up and running."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/ready", status_code=status.HTTP_200_OK, tags=["Health"])
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """Readiness probe: validates database connectivity before accepting incoming traffic."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "disconnected", "error": str(e)}


@app.get("/", tags=["Root"])
def root():
    return {
        "portal": settings.APP_NAME,
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/ready",
        "metrics_url": "/metrics",
    }


# Include API v1 routes
app.include_router(api_router)
