from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.redis_client import redis_client
from app.schemas.response import Response
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=Response)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        if redis_client.client and redis_client.client.ping():
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "disconnected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["redis"] = "disconnected"
    
    return Response(
        code=200 if health_status["status"] == "healthy" else 503,
        message=health_status["status"],
        data=health_status
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"message": "pong"}
